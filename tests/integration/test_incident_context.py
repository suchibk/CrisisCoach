import pytest
from pydantic import ValidationError
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models.incident_context import IncidentContext
from crisis_coach.models.events import IncidentContextEvent
from crisis_coach.persistence.sqlite import SQLiteIncidentRepository
from crisis_coach.tools.capture import build_capture_executor


def test_context_persists_preserves_timer_and_exports(tmp_path):
    repo = SQLiteIncidentRepository(tmp_path / "incidents.db")
    coach = CollisionWorkflow(repository=repo, executor=build_capture_executor(tmp_path / "attachments"))
    state, _ = coach.start()
    for answer in ("No", "No", "Yes"): coach.turn(state, answer)
    task, timer = state.last_instruction, state.timer_deadline
    coach.turn(state, '/context {"occurred_at":"2026-09-11T14:30:00-04:00","location":"Oak Street","weather":"Rain"}')
    assert state.incident_context.location == "Oak Street"
    assert (state.last_instruction, state.timer_deadline) == (task, timer)
    assert repo.load(state.incident_id).incident_context == state.incident_context
    pytest.importorskip("docx")
    from docx import Document
    coach.turn(state, "/export")
    text = "\n".join(p.text for p in Document(tmp_path / "exports" / state.exports[-1].relative_path).paragraphs)
    assert "Oak Street" in text and "Rain" in text and "2026-09-11T14:30:00-04:00" in text
    reopened, _ = coach.reopen(state.incident_id)
    assert reopened.incident_context == state.incident_context


@pytest.mark.parametrize("paused", [False, True])
def test_injury_context_preempts_even_when_paused(paused):
    coach = CollisionWorkflow()
    state, _ = coach.start()
    for answer in ("No", "No", "Yes"): coach.turn(state, answer)
    if paused: coach.turn(state, "pause")
    reply = coach.handle_event(state, IncidentContextEvent(context=IncidentContext(location="My chest hurts")))
    assert reply.terminate and state.status is SessionStatus.STOOD_DOWN
    assert state.incident_context.location is None


def test_context_cannot_bypass_safety_or_pause():
    coach = CollisionWorkflow()
    state, _ = coach.start()
    event = IncidentContextEvent(context=IncidentContext(location="Oak Street"))
    coach.handle_event(state, event)
    assert state.incident_context.location is None
    for answer in ("No", "No", "Yes"): coach.turn(state, answer)
    coach.turn(state, "pause")
    coach.handle_event(state, IncidentContextEvent(context=event.context))
    assert state.incident_context.location is None


def test_time_requires_offset_and_legacy_state_defaults():
    with pytest.raises(ValidationError): IncidentContext(occurred_at="2026-09-11T14:30:00")
    from crisis_coach.models import SceneState
    assert SceneState(incident_id="legacy", person_name="Test").incident_context == IncidentContext()
