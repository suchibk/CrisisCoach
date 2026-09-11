import base64
import hashlib
import sqlite3
import pytest
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models.evidence import EvidenceStatus
from crisis_coach.models.events import CaptureEvent
from crisis_coach.tools.capture import build_capture_executor
from crisis_coach.tools.contracts import ToolContext, ToolSpec, FileCaptureArgs, ToolError, ApprovalRequired
from crisis_coach.tools.registry import ToolRegistry, ToolRegistration
from crisis_coach.tools.executor import ToolExecutor
from crisis_coach.persistence.sqlite import SQLiteIncidentRepository
from crisis_coach.persistence.contracts import PersistenceError

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOZsAAAAASUVORK5CYII=")

@pytest.fixture
def setup(tmp_path):
    store = tmp_path / "attachments"
    repo = SQLiteIncidentRepository(tmp_path / "incidents.db")
    coach = CollisionWorkflow(repository=repo, executor=build_capture_executor(store))
    state, _ = coach.start()
    for text in ("No", "No", "Yes"): coach.turn(state, text)
    photo = tmp_path / "source.png"
    photo.write_bytes(PNG)
    return coach, state, repo, store, photo


def test_photo_copied_and_recovered_without_claiming_verification(setup):
    coach, state, repo, store, photo = setup
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    record = repo.load(state.incident_id).evidence["wide_scene_photo"]
    assert record.status is EvidenceStatus.COLLECTED
    assert record.attachments[0].sha256 == hashlib.sha256(PNG).hexdigest()
    assert (store / record.attachments[0].relative_path).read_bytes() == PNG
    photo.unlink()
    recovered, _ = coach.reopen(state.incident_id)
    assert recovered.evidence["wide_scene_photo"].attachments == record.attachments
    assert "not been verified" in record.note


def test_statement_is_stored_verbatim_without_changing_scenario(setup):
    coach, state, repo, store, _ = setup
    text = "I stopped near a bollard.\nThe other vehicle hit mine."
    coach.handle_event(state, CaptureEvent(item_id="statement", tool="record_statement", arguments={"text": text}))
    record = state.evidence["statement"]
    assert record.original_text == text
    assert (store / record.attachments[0].relative_path).read_text(encoding="utf-8") == text
    assert state.domain_data["scenario"] == "full"


def test_injury_in_statement_preempts_storage(setup):
    coach, state, _, store, _ = setup
    reply = coach.turn(state, "/statement statement My chest hurts")
    assert reply.terminate
    assert state.status is SessionStatus.STOOD_DOWN
    assert not store.exists()


def test_pause_and_incomplete_safety_block_file_capture(setup):
    coach, state, _, store, photo = setup
    coach.turn(state, "pause")
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert not store.exists()
    new, _ = coach.start()
    coach.turn(new, f"/attach wide_scene_photo {photo}")
    assert not store.exists()


def test_replay_does_not_reread_deleted_source(setup):
    coach, state, repo, store, photo = setup
    event = CaptureEvent(item_id="wide_scene_photo", tool="capture_photo", arguments={"source_path": str(photo)})
    coach.handle_event(state, event)
    photo.unlink()
    assert coach.handle_event(state, event) is None
    assert len(list(store.rglob("*.png"))) == 1


def test_duplicate_content_is_not_duplicated(setup):
    coach, state, _, store, photo = setup
    for _ in range(2): coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert len(state.evidence["wide_scene_photo"].attachments) == 1
    assert len(list(store.rglob("*.png"))) == 1


def test_wrong_tool_unknown_item_and_nonimage_are_rejected(setup):
    coach, state, _, store, photo = setup
    coach.turn(state, f"/attach statement {photo}")
    coach.turn(state, f"/attach unknown {photo}")
    assert not store.exists()
    photo.write_text("not an image")
    reply = coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert "JPEG and PNG" in reply.text
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.PENDING


def test_failed_database_commit_does_not_mark_capture_complete(setup):
    coach, state, repo, store, photo = setup
    with sqlite3.connect(repo.path) as db:
        db.execute("CREATE TRIGGER fail BEFORE INSERT ON incident_events BEGIN SELECT RAISE(ABORT, 'test'); END")
    with pytest.raises(PersistenceError): coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.PENDING
    assert repo.load(state.incident_id).evidence["wide_scene_photo"].status is EvidenceStatus.PENDING
    # Immutable unreferenced blobs may remain; retry reuses them safely.
    assert len(list(store.rglob("*.png"))) == 1


def test_executor_blocks_external_tools_and_extra_arguments(tmp_path):
    registry = ToolRegistry()
    called = []
    registry.register(ToolRegistration(ToolSpec(name="external", external=True), FileCaptureArgs, lambda *args: called.append(1)))
    with pytest.raises(ApprovalRequired):
        ToolExecutor(registry).execute("external", {"source_path": "x"}, ToolContext(incident_id="x", event_id="y"))
    assert not called
    with pytest.raises(ToolError):
        build_capture_executor(tmp_path).execute("capture_photo", {"source_path": "x", "approved": True}, ToolContext(incident_id="x", event_id="y"))


def test_statement_injury_survives_database_read_failure(setup, monkeypatch):
    coach, state, repo, store, _ = setup
    def fail(*args): raise PersistenceError("offline disk")
    monkeypatch.setattr(repo, "has_event", fail)
    reply = coach.turn(state, "/statement statement My chest hurts")
    assert reply.terminate and "could not be saved" in reply.text
    assert state.status is SessionStatus.STOOD_DOWN
    assert not store.exists()


def test_capture_through_langgraph(tmp_path):
    pytest.importorskip("langgraph")
    coach = CollisionWorkflow(backend="langgraph", executor=build_capture_executor(tmp_path / "attachments"))
    state, _ = coach.start()
    for text in ("No", "No", "Yes"): coach.turn(state, text)
    photo = tmp_path / "photo.png"
    photo.write_bytes(PNG)
    coach.turn(state, f"/attach wide_scene_photo {photo}")
    assert state.evidence["wide_scene_photo"].status is EvidenceStatus.COLLECTED
    assert coach.last_route == ("safety", "controls", "gate", "capture", "plan")
