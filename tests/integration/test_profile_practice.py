import hashlib
import json
from pathlib import Path
import pytest
from crisis_coach.models.profile import Profile
from crisis_coach.persistence.profiles import ProfileRepository
from crisis_coach.persistence.contracts import PersistenceError
from crisis_coach.practice.runtime import PracticeRuntime,fixture_bytes


def test_profile_conflict_and_snapshot(tmp_path):
    repo=ProfileRepository(tmp_path / "profile.sqlite3")
    initial=repo.load()
    saved=repo.save(Profile(name="Alex",vehicle="Test car",policy_id="user-policy"))
    assert repo.load() == saved
    with pytest.raises(PersistenceError): repo.save(initial)
    with PracticeRuntime() as run:
        state,_=run.coach.start(saved.name,profile=saved)
        repo.save(saved.model_copy(update={"vehicle":"Replacement"}))
        reopened,_=run.coach.reopen(state.incident_id)
        assert reopened.profile.vehicle == "Test car"
        assert reopened.knowledge_context.policy_id is None


def test_practice_ignores_real_settings_and_removes_only_temporary_data(tmp_path,monkeypatch):
    live=tmp_path / "live";live.mkdir()
    marker=live / "keep.txt";marker.write_text("keep")
    monkeypatch.setenv("CRISIS_COACH_DATA_DIR",str(live))
    monkeypatch.setenv("CRISIS_COACH_KNOWLEDGE_DIR",str(live / "missing"))
    monkeypatch.setenv("CRISIS_COACH_AI_API_KEY","must-not-use")
    monkeypatch.setenv("ELEVENLABS_API_KEY","must-not-use")
    with PracticeRuntime("Marcus · unattended damage") as run:
        root=run.root
        for text in ["No","No","Yes"]: run.submit(text)
        assert run.scene.current_evidence_id == "footage_reference"
        assert run.scene.profile.name.startswith("Marcus")
        assert run.coach.pack.ai_classifier is None and run.coach.pack.interpreter is None
        run.submit('/knowledge-demo')
        reply=run.submit('/ask Do I need to call the police?')
        assert reply.citations and all(c.synthetic for c in reply.citations)
    assert not root.exists() and marker.read_text() == "keep"
    assert list(live.iterdir()) == [marker]


def test_fixtures_and_trace_are_durable():
    from importlib.resources import files
    manifest=json.loads(files("crisis_coach.practice").joinpath("fixtures/manifest.json").read_text())
    for item in manifest:
        assert hashlib.sha256(fixture_bytes(item["file"].split('.')[0])).hexdigest() == item["sha256"]
    with PracticeRuntime() as run:
        for text in ["No","No","Yes"]: run.submit(text)
        run.capture("retake")
        run.capture("retake")
        assert run.reviewer.calls == 1
        saved=run.repo.load(run.scene.incident_id)
        assert saved.trace == run.scene.trace
        assert saved.evidence["wide_scene_photo"].failed_photo_reviews == 1
