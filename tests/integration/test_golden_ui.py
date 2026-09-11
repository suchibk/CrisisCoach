from pathlib import Path
import pytest
pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest
from crisis_coach.practice.runtime import PracticeRuntime

APP=Path("src/crisis_coach/interfaces/streamlit_app.py").resolve()

def run_practice():
    app=AppTest.from_file(APP,default_timeout=15)
    app.session_state["mode"]="Practice"
    app.run()
    assert not app.exception
    return app


def clear_gates(app):
    for index in range(3):
        app.button(key="practice_prompt_0").click().run()
        assert not app.exception


def test_practice_gates_photo_theme_and_safety_controls():
    app=run_practice()
    try:
        assert app.session_state.scene.current_evidence_id is None
        clear_gates(app)
        assert app.session_state.scene.current_evidence_id == "wide_scene_photo"
        app.button(key="practice_prompt_0").click().run()
        assert app.session_state.scene.current_evidence_id == "other_plate"
        app.button(key="practice_photo_retake").click().run()
        assert app.session_state.scene.evidence["other_plate"].failed_photo_reviews == 1
        app.button(key="practice_photo_usable").click().run()
        assert app.session_state.scene.evidence["other_plate"].status.value == "verified"
        incident=app.session_state.scene.incident_id
        app.radio(key="appearance").set_value("Light").run()
        assert app.session_state.scene.incident_id == incident
        app.button(key="control_pause").click().run()
        assert app.session_state.scene.status.value == "stopped"
        assert not list(app.get("file_uploader"))
        app.button(key="control_pause").click().run()
        app.button(key="practice_prompt_4").click().run()
        assert app.session_state.scene.status.value == "stood_down"
        assert app.button(key="control_pause").disabled
        assert not list(app.get("file_uploader"))
        app.button(key="reopen_safety").click().run()
        assert app.session_state.scene.safety_gate.value == "danger_reentry"
        assert not app.exception
    finally: app.session_state.practice.close()


def test_practice_reset_and_report():
    app=run_practice()
    try:
        original=app.session_state.practice.root
        app.selectbox(key="practice_scenario").select("Priya · minor scuff").run()
        app.button(key="reset_practice").click().run()
        assert not original.exists()
        clear_gates(app)
        for _ in range(2): app.button(key="practice_photo_usable").click().run()
        app.text_area(key=f"text_{app.session_state.scene.incident_id}_statement").set_value("I reversed into a bollard.").run()
        app.button(key="save_statement").click().run()
        app.radio(key="view").set_value("Evidence pack").run()
        app.button(key="build_pack").click().run()
        assert app.session_state.scene.exports[-1].stored_items == 3
        assert len(app.get("download_button")) == 1
        assert not app.exception
    finally: app.session_state.practice.close()


def test_live_practice_switch_and_profile(tmp_path,monkeypatch):
    import crisis_coach.bootstrap as bootstrap
    from crisis_coach import CollisionWorkflow
    from crisis_coach.persistence.sqlite import SQLiteIncidentRepository
    monkeypatch.setenv("CRISIS_COACH_DATA_DIR",str(tmp_path))
    repo=SQLiteIncidentRepository(tmp_path / "incidents.sqlite3")
    monkeypatch.setattr(bootstrap,"build_repository",lambda:repo)
    monkeypatch.setattr(bootstrap,"build_coach",lambda:CollisionWorkflow(repository=repo))
    app=AppTest.from_file(APP,default_timeout=15).run()
    live_id=app.session_state.scene.incident_id
    app.radio(key="view").set_value("Profile").run()
    app.text_input(key="profile_name").set_value("Alex").run()
    next(b for b in app.button if b.label=="Save profile").click().run()
    app.radio(key="mode").set_value("Practice").run()
    root=app.session_state.practice.root
    assert app.session_state.scene.profile.name != "Alex"
    assert len(repo.list_incidents()) == 1
    app.radio(key="mode").set_value("Live incident").run()
    assert not root.exists()
    assert app.session_state.scene.incident_id == live_id
    next(b for b in app.button if b.label=="New incident").click().run()
    assert app.session_state.scene.profile.name == "Alex"
    assert not app.exception
