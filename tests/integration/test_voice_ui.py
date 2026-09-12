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
    app.checkbox(key="voice_auto").check().run()
    app.run()
    assert provider.calls == 1  # Cached audio is not synthesized on fragment reruns.
    app.session_state.messages.append(("assistant", "Next coach response"))
    app.run()
    pending = app.session_state.voice_controller.pending
    if pending:
        pending.result(timeout=2)
    app.run()
    assert not app.exception
    assert provider.calls == 2
    assert app.session_state.voice_controller.audio is not None
    next(button for button in app.button if button.label == "New incident").click().run()
    assert not app.exception
    assert not app.session_state.voice_controller.playback_allowed
    assert app.session_state.voice_controller.audio is None


def test_voice_setup_and_disconnect(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import crisis_coach.interfaces.voice.view as view
    monkeypatch.setenv("CRISIS_COACH_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(view, "build_voice_provider", lambda: None)
    app = AppTest.from_file(Path("src/crisis_coach/interfaces/streamlit_app.py").resolve(), default_timeout=10).run()
    assert not app.exception
    app.text_input[0].set_value("demo-secret")
    app.text_input[1].set_value("demo_voice")
    next(b for b in app.button if b.label == "Connect ElevenLabs").click().run()
    assert not app.exception
    assert app.session_state.voice_controller.provider.settings.voice_id == "demo_voice"
    assert not app.session_state.voice_controller.playback_allowed
    assert "demo-secret" not in repr(app.session_state.voice_controller.provider.settings)
    app.button(key="voice_disconnect").click().run()
    assert not app.exception
    assert any(b.label == "Connect ElevenLabs" for b in app.button)
    assert "voice_controller" not in app.session_state


def test_microphone_keeps_timer_from_discarding_transcript(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from crisis_coach import CollisionWorkflow, SessionStatus
    from crisis_coach.models import SafetyGate
    from crisis_coach.interfaces.voice.contracts import Transcript
    import crisis_coach.bootstrap as bootstrap
    import crisis_coach.interfaces.voice.view as view

    class Clock:
        time = 0
        def now(self): return self.time

    clock = Clock()
    monkeypatch.setenv("CRISIS_COACH_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(bootstrap, "build_coach", lambda: CollisionWorkflow(clock=clock))
    monkeypatch.setattr(view, "build_voice_provider", lambda: object())
    app = AppTest.from_file(Path("src/crisis_coach/interfaces/streamlit_app.py").resolve(), default_timeout=10).run()
    app.button(key="voice_allow_microphone").click().run()
    controller = app.session_state.voice_controller
    controller.transcript = Transcript(text="I am not hurt")
    generation = controller.generation
    for elapsed in (8, 16, 60):
        clock.time = elapsed
        app.run()
        assert not app.exception
        assert controller.generation == generation
        assert controller.transcript.text == "I am not hurt"
        assert app.session_state.scene.status is SessionStatus.ACTIVE
        assert app.session_state.scene.unanswered_safety_turns == 0
    next(b for b in app.button if b.label == "Send reviewed answer").click().run()
    assert not app.exception
    assert app.session_state.scene.safety_gate is SafetyGate.OTHER_INJURY
    assert app.session_state.scene.status is SessionStatus.ACTIVE
