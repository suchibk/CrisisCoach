import pytest
from pathlib import Path


def test_voice_ui_opt_in_and_new_incident_reset(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from crisis_coach import CollisionWorkflow
    from crisis_coach.persistence.sqlite import SQLiteIncidentRepository
    import crisis_coach.bootstrap as bootstrap
    import crisis_coach.interfaces.voice.view as view
    from crisis_coach.interfaces.voice.contracts import SpeechAudio, Transcript

    class Provider:
        calls = 0
        def speak(self, instruction):
            self.calls += 1
            return SpeechAudio(data=b"ID3fake")
        def transcribe(self, recording):
            raise AssertionError("No recording should be uploaded")
    provider = Provider()
    repo = SQLiteIncidentRepository(tmp_path / "incidents.db")
    monkeypatch.setattr(bootstrap, "build_repository", lambda: repo)
    monkeypatch.setattr(bootstrap, "build_coach", lambda: CollisionWorkflow(repository=repo))
    monkeypatch.setattr(view, "build_voice_provider", lambda: provider)
    app = AppTest.from_file(Path("src/crisis_coach/interfaces/streamlit_app.py").resolve(), default_timeout=10).run()
    assert not app.exception
    assert provider.calls == 0
    app.button(key="voice_allow_playback").click().run()
    assert not app.exception
    assert app.session_state.voice_controller.playback_allowed
    assert provider.calls == 0
    app.button(key="voice_speak").click().run()
    pending = app.session_state.voice_controller.pending
    if pending:
        pending.result(timeout=2)
    app.run()
    assert not app.exception
    assert provider.calls == 1
    assert app.session_state.voice_controller.audio is not None
    next(button for button in app.button if button.label == "New incident").click().run()
    assert not app.exception
    assert not app.session_state.voice_controller.playback_allowed
    assert app.session_state.voice_controller.audio is None
