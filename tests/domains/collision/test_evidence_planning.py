from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.domains.collision.pack import CollisionPack
from crisis_coach.models.evidence import EvidenceStatus, EvidenceCatalogue
from crisis_coach.orchestration.engine import WorkflowEngine
from crisis_coach.persistence.sqlite import SQLiteIncidentRepository

NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)

def scene(description=None, repo=None):
    pack = CollisionPack(now=lambda: NOW)
    coach = WorkflowEngine(pack, repository=repo)
    state, _ = coach.start()
    if description:
        coach.turn(state, description)
    for answer in ("No", "No", "Yes"):
        coach.turn(state, answer)
    return coach, state


def test_priya_witness_interrupt_then_resume_without_repeating_photo():
    coach, state = scene()
    assert state.current_evidence_id == "wide_scene_photo"
    coach.turn(state, "Photo taken")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.REPORTED
    coach.turn(state, "There's a woman who saw it. She's walking off.")
    assert state.current_evidence_id == "witness_details"
    coach.turn(state, "/collected witness_details Maya, 555-0100")
    assert state.current_evidence_id == "other_plate"
    assert state.evidence_requests.count("wide_scene_photo") == 1


def test_departing_driver_reorders_and_repeated_signals_do_not_extend_window():
    coach, state = scene()
    coach.turn(state, "He's getting back into his car")
    assert state.current_evidence_id == "other_plate"
    deadline = state.evidence["other_plate"].estimated_deadline
    coach.pack.now = lambda: NOW + timedelta(seconds=20)
    coach.turn(state, "He's getting back into his car")
    assert state.evidence["other_plate"].estimated_deadline == deadline
    assert state.last_decision.candidates[0].seconds_remaining == 40
    coach.turn(state, "photo taken")
    assert state.current_evidence_id == "other_insurance"


def test_marcus_has_no_driver_tasks():
    coach, state = scene("I came back to my parked car. Nobody there.")
    assert state.current_evidence_id == "footage_reference"
    assert all(not item.item_id.startswith("other_") for item in state.last_decision.candidates)
    coach.turn(state, "/collected footage_reference Camera by bay 12; service desk contact noted")
    assert state.current_evidence_id == "own_damage"


def test_scuff_collects_only_relevant_items():
    coach, state = scene("I scraped a bollard")
    assert state.current_evidence_id == "own_damage"
    coach.turn(state, "done")
    assert state.current_evidence_id == "object_photo"
    coach.turn(state, "done")
    assert state.current_evidence_id == "statement"
    reply = coach.turn(state, "/collected statement I reversed into the bollard.")
    assert state.current_evidence_id is None
    assert "not verified" in reply.text
    assert state.status is SessionStatus.ACTIVE  # No report has been assembled.


def test_dana_injury_prevents_evidence_updates():
    coach, state = scene()
    before = {key: value.model_dump() for key, value in state.evidence.items()}
    reply = coach.turn(state, "Done, but my chest hurts")
    assert reply.terminate
    assert {key: value.model_dump() for key, value in state.evidence.items()} == before
    assert coach.last_route == ("safety",)


def test_driver_departure_preserves_honest_gaps_and_prior_reports():
    coach, state = scene()
    coach.turn(state, "done")
    coach.turn(state, "he drove off")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.REPORTED
    assert state.evidence["other_plate"].status is EvidenceStatus.UNAVAILABLE
    assert state.current_evidence_id == "own_damage"
    assert "Other vehicle plate" in coach.turn(state, "/missing").text


def test_invalid_item_report_does_not_add_fictitious_evidence():
    coach, state = scene()
    reply = coach.turn(state, "/collected invented pretend")
    assert "not applicable" in reply.text
    assert "invented" not in state.evidence


def test_text_items_require_actual_text_not_done():
    coach, state = scene("I scraped a bollard")
    coach.turn(state, "done")
    coach.turn(state, "done")
    coach.turn(state, "done")
    assert state.evidence["statement"].status is EvidenceStatus.PENDING


def test_recovery_preserves_reports_deadlines_and_decisions(tmp_path):
    repo = SQLiteIncidentRepository(tmp_path / "incidents.db")
    coach, state = scene(repo=repo)
    coach.turn(state, "done")
    coach.turn(state, "driver is leaving")
    recovered, _ = coach.reopen(state.incident_id)
    assert recovered.evidence["wide_scene_photo"].status is EvidenceStatus.REPORTED
    assert recovered.last_decision == state.last_decision
    assert recovered.evidence["other_plate"].estimated_deadline == NOW + timedelta(seconds=60)


def test_ordering_is_reproducible():
    decisions = []
    for _ in range(2):
        coach, state = scene()
        coach.turn(state, "driver is leaving")
        decisions.append(state.last_decision)
    assert decisions[0] == decisions[1]


def test_duplicate_catalogue_ids_rejected():
    data = CollisionPack().catalogue.model_dump()
    data["items"] = (data["items"][0], data["items"][0])
    with pytest.raises(ValidationError): EvidenceCatalogue.model_validate(data)


def test_failed_item_is_excluded_and_missing_report_is_honest():
    coach, state = scene()
    coach.turn(state, "/failed wide_scene_photo Camera unavailable")
    assert state.current_evidence_id == "other_plate"
    assert "Wide scene" in coach.turn(state, "/missing").text


def test_witness_departure_retains_gap():
    coach, state = scene()
    coach.turn(state, "There's a witness walking away")
    coach.turn(state, "witness has left")
    assert state.evidence["witness_details"].status is EvidenceStatus.UNAVAILABLE
    assert state.current_evidence_id != "witness_details"


def test_catalogue_version_mismatch_blocks_updates():
    coach, state = scene()
    state.evidence_catalogue_version = "future"
    with pytest.raises(ValueError): coach.turn(state, "done")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.PENDING


def test_report_content_does_not_change_scenario():
    coach, state = scene()
    coach.turn(state, "/collected statement I was parked near a bollard when the other car hit mine.")
    assert state.domain_data["scenario"] == "full"
    assert state.evidence["statement"].status is EvidenceStatus.REPORTED
