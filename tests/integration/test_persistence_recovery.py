import sqlite3
import pytest
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models import SafetyGate
from crisis_coach.models.events import TextEvent
from crisis_coach.persistence.sqlite import SQLiteIncidentRepository
from crisis_coach.persistence.contracts import PersistenceError, ConcurrentUpdateError

class Clock:
    def __init__(self, time=100): self.time = time
    def now(self): return self.time

@pytest.fixture
def repo(tmp_path):
    return SQLiteIncidentRepository(tmp_path / "data" / "incidents.sqlite3")


def test_dana_survives_repository_restart_and_requires_medical_check(repo):
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    coach.turn(state, "My chest hurts")
    restarted = SQLiteIncidentRepository(repo.path)
    assert restarted.load(state.incident_id).status is SessionStatus.STOOD_DOWN
    coach = CollisionWorkflow(repository=restarted)
    recovered, reply = coach.reopen(state.incident_id)
    assert "medical checked" in reply.text
    assert recovered.timer_id is None
    coach.turn(recovered, "No")
    assert recovered.status is SessionStatus.STOOD_DOWN
    coach.turn(recovered, "Yes, a doctor checked me")
    assert recovered.safety_gate is SafetyGate.USER_INJURY
    assert not recovered.evidence_requests


def test_active_recovery_rechecks_safety_and_uses_fresh_clock(repo):
    coach = CollisionWorkflow(repository=repo, clock=Clock(10000))
    state, _ = coach.start()
    for answer in ("No", "No", "Yes"):
        coach.turn(state, answer)
    stored = repo.load(state.incident_id)
    assert stored.timer_deadline is None
    assert stored.timer_id is None
    restarted = CollisionWorkflow(repository=repo, clock=Clock(10))
    recovered, reply = restarted.reopen(state.incident_id)
    assert recovered.safety_gate is SafetyGate.USER_INJURY
    assert reply.expects == "yes_or_no"
    assert restarted.seconds_until_timer(recovered) == 8
    assert recovered.evidence_requests == ["wide_scene_photo"]


def test_paused_recovery_stays_paused(repo):
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    coach.turn(state, "stop")
    recovered, _ = coach.reopen(state.incident_id)
    assert recovered.status is SessionStatus.STOPPED
    assert recovered.timer_id is None
    assert coach.turn(recovered, "go on").text == "Are you hurt anywhere?"


def test_old_event_replay_after_other_events_and_restart_is_ignored(repo):
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    first = TextEvent(text="No")
    coach.handle_event(state, first)
    coach.turn(state, "No")
    recovered, _ = coach.reopen(state.incident_id)
    before = recovered.model_dump()
    assert coach.handle_event(recovered, first) is None
    assert recovered.model_dump() == before


def test_conflicting_writer_cannot_change_memory_or_database(repo):
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    stale = repo.load(state.incident_id)
    coach.turn(state, "No")
    before = stale.model_dump()
    with pytest.raises(ConcurrentUpdateError):
        coach.turn(stale, "No")
    assert stale.model_dump() == before
    assert repo.load(state.incident_id).safety_gate is SafetyGate.OTHER_INJURY


def test_event_and_response_are_saved_together(repo):
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    event = TextEvent(text="My chest hurts")
    coach.handle_event(state, event)
    with sqlite3.connect(repo.path) as db:
        row = db.execute("SELECT event_json, response_json, revision FROM incident_events").fetchone()
    assert event.event_id in row[0]
    assert "call 911" in row[1]
    assert row[2] == repo.load(state.incident_id).revision


def test_storage_failure_does_not_suppress_safety(repo, monkeypatch):
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    def fail(*args, **kwargs): raise PersistenceError("disk failure")
    monkeypatch.setattr(repo, "save", fail)
    reply = coach.turn(state, "My chest hurts")
    assert reply.terminate and "could not be saved" in reply.text
    assert state.status is SessionStatus.STOOD_DOWN


def test_missing_corrupt_and_future_incidents_fail_explicitly(repo):
    with pytest.raises(KeyError): repo.load("missing")
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    with sqlite3.connect(repo.path) as db:
        db.execute("UPDATE incidents SET state_json = 'invalid'")
    with pytest.raises(PersistenceError): repo.load(state.incident_id)
    with sqlite3.connect(repo.path) as db:
        db.execute("PRAGMA user_version = 99")
    with pytest.raises(PersistenceError): SQLiteIncidentRepository(repo.path)


def test_event_insert_failure_rolls_back_snapshot_and_memory(repo):
    coach = CollisionWorkflow(repository=repo)
    state, _ = coach.start()
    before = state.model_dump()
    with sqlite3.connect(repo.path) as db:
        db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON incident_events BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    with pytest.raises(PersistenceError):
        coach.turn(state, "No")
    assert state.model_dump() == before
    saved = repo.load(state.incident_id)
    assert saved.revision == state.revision
    assert saved.safety_gate is SafetyGate.USER_INJURY
    with sqlite3.connect(repo.path) as db:
        assert db.execute("SELECT count(*) FROM incident_events").fetchone()[0] == 0
