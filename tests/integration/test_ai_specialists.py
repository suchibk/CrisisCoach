import base64
import pytest
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models.ai import SceneInterpretation, SceneObservation, PhotoAssessment
from crisis_coach.models.evidence import EvidenceStatus
from crisis_coach.tools.capture import build_capture_executor
from crisis_coach.persistence.attachments import AttachmentStore
from crisis_coach.persistence.sqlite import SQLiteIncidentRepository

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOZsAAAAASUVORK5CYII=")

class Interpreter:
    def __init__(self, result): self.result, self.calls = result, []
    def interpret(self, text):
        self.calls.append(text)
        if isinstance(self.result, Exception): raise self.result
        return self.result

class Reviewer:
    def __init__(self, results): self.results, self.calls = iter(results), []
    def review(self, data, media, goal):
        self.calls.append((data, media, goal))
        result = next(self.results)
        if isinstance(result, Exception): raise result
        return result


def setup(tmp_path, interpreter=None, reviewer=None, backend="local"):
    root = tmp_path / "attachments"
    coach = CollisionWorkflow(backend=backend, interpreter=interpreter, photo_reviewer=reviewer,
        attachment_store=AttachmentStore(root), executor=build_capture_executor(root),
        repository=SQLiteIncidentRepository(tmp_path / "incidents.db"))
    state, _ = coach.start()
    for text in ("No", "No", "Yes"): coach.turn(state, text)
    return coach, state


def test_scene_ai_requires_consent_and_confirmation(tmp_path):
    text = "The person who saw everything is heading home"
    interpreter = Interpreter(SceneInterpretation(observations=(SceneObservation(signal="witness_leaving", supporting_quote=text),)))
    coach, state = setup(tmp_path, interpreter=interpreter)
    coach.turn(state, text)
    assert not interpreter.calls
    coach.turn(state, "/ai-text on")
    reply = coach.turn(state, text)
    assert "confirm scene" in reply.text
    assert state.current_evidence_id == "wide_scene_photo"
    coach.turn(state, "confirm scene")
    assert state.current_evidence_id == "witness_details"


def test_ungrounded_or_malformed_scene_output_is_ignored(tmp_path):
    interpreter = Interpreter(SceneInterpretation(observations=(SceneObservation(signal="driver_left", supporting_quote="not in utterance"),)))
    coach, state = setup(tmp_path, interpreter=interpreter)
    coach.turn(state, "/ai-text on")
    coach.turn(state, "The man is over there")
    assert not state.pending_scene_changes
    assert state.current_evidence_id == "wide_scene_photo"
    assert any("AI_SCENE_FAILED" in event for event in state.events)


def test_deterministic_injury_skips_scene_ai_and_ai_can_only_escalate(tmp_path):
    interpreter = Interpreter(SceneInterpretation(possible_injury=True))
    coach, state = setup(tmp_path, interpreter=interpreter)
    coach.turn(state, "/ai-text on")
    assert coach.turn(state, "My chest hurts").terminate
    assert not interpreter.calls
    other, _ = coach.start()
    for text in ("No", "No", "Yes", "/ai-text on"): coach.turn(other, text)
    assert coach.turn(other, "Something feels very wrong inside").terminate
    assert other.status is SessionStatus.STOOD_DOWN


def test_scene_timeout_preserves_local_workflow(tmp_path):
    interpreter = Interpreter(TimeoutError())
    coach, state = setup(tmp_path, interpreter=interpreter)
    coach.turn(state, "/ai-text on")
    coach.turn(state, "The man is over there")
    assert state.status is SessionStatus.ACTIVE
    assert not state.pending_scene_changes


def test_photo_consent_usable_result_and_reopen_reset(tmp_path):
    reviewer = Reviewer([PhotoAssessment(verdict="usable")])
    coach, state = setup(tmp_path, reviewer=reviewer)
    photo = tmp_path / "photo.png"
    photo.write_bytes(PNG)
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert not reviewer.calls
    coach.turn(state, "/ai-images on")
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert len(reviewer.calls) == 1
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.VERIFIED
    recovered, _ = coach.reopen(state.incident_id)
    assert not recovered.ai_images_allowed and not recovered.ai_text_allowed
    assert recovered.evidence["wide_scene_photo"].photo_reviews


def test_two_distinct_failed_photos_stop_reasking_and_preserve_originals(tmp_path):
    assessment = PhotoAssessment(verdict="retake", issues=("blur",))
    reviewer = Reviewer([assessment, assessment])
    coach, state = setup(tmp_path, reviewer=reviewer)
    coach.turn(state, "/ai-images on")
    photo = tmp_path / "photo.png"
    photo.write_bytes(PNG)
    assert "Retake" in coach.turn(state, f"/attach wide_scene_photo {photo}").text
    # Same bytes reuse the cached assessment and do not consume another attempt.
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert len(reviewer.calls) == 1
    photo.write_bytes(PNG + b"different")
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    record = state.evidence["wide_scene_photo"]
    assert record.status is EvidenceStatus.FAILED
    assert record.failed_photo_reviews == 2 and len(record.attachments) == 2
    assert state.current_evidence_id != "wide_scene_photo"


def test_review_timeout_keeps_file_collected_not_verified(tmp_path):
    reviewer = Reviewer([TimeoutError()])
    coach, state = setup(tmp_path, reviewer=reviewer)
    coach.turn(state, "/ai-images on")
    photo = tmp_path / "photo.png"
    photo.write_bytes(PNG)
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.COLLECTED
    assert "unavailable" in state.evidence["wide_scene_photo"].note


def test_rejected_scene_proposal_does_not_change_applicability(tmp_path):
    interpreter = Interpreter(SceneInterpretation(observations=(SceneObservation(signal="unattended", supporting_quote="I wasn't there"),)))
    coach, state = setup(tmp_path, interpreter=interpreter)
    coach.turn(state, "/ai-text on")
    coach.turn(state, "I wasn't there")
    coach.turn(state, "reject scene")
    assert state.domain_data["scenario"] == "full"
    assert not state.pending_scene_changes


def test_usable_photo_is_not_downgraded_by_later_bad_image(tmp_path):
    reviewer = Reviewer([PhotoAssessment(verdict="usable"), PhotoAssessment(verdict="retake", issues=("blur",))])
    coach, state = setup(tmp_path, reviewer=reviewer)
    coach.turn(state, "/ai-images on")
    photo = tmp_path / "photo.png"
    photo.write_bytes(PNG)
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    photo.write_bytes(PNG + b"different")
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.VERIFIED
    assert len(state.evidence["wide_scene_photo"].attachments) == 2


def test_langgraph_specialist_consent_and_capture(tmp_path):
    pytest.importorskip("langgraph")
    reviewer = Reviewer([PhotoAssessment(verdict="usable")])
    coach, state = setup(tmp_path, reviewer=reviewer, backend="langgraph")
    coach.turn(state, "/ai-images on")
    assert state.ai_images_allowed
    photo = tmp_path / "photo.png"
    photo.write_bytes(PNG)
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.VERIFIED
    coach.turn(state, "/ai-images off")
    assert not state.ai_images_allowed
