from concurrent.futures import Future
from io import BytesIO
import json
import wave
import pytest
from pydantic import ValidationError
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models.responses import Instruction
from crisis_coach.interfaces.voice.contracts import Recording, SpeechAudio, Transcript, VoiceError
from crisis_coach.interfaces.voice.controller import VoiceController
from crisis_coach.interfaces.voice.elevenlabs import ElevenLabsSettings, ElevenLabsVoice, build_voice_provider


def wav(seconds=1):
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * int(seconds * 16000))
    return output.getvalue()


@pytest.mark.parametrize("data", [b"not audio", wav(31), wav(0.05), wav()[:-10]], ids=["invalid", "too-long", "too-short", "truncated"])
def test_recording_validation(data):
    with pytest.raises(ValidationError):
        Recording(data=data)


def test_valid_recording_and_private_repr():
    recording = Recording(data=wav())
    assert recording.data == wav()
    assert "data=" not in repr(recording)
    with pytest.raises(ValidationError):
        Transcript(text=" ")


def test_unconfigured_voice_is_optional(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    assert build_voice_provider() is None
    with pytest.raises(ValidationError):
        ElevenLabsSettings(api_key=" ", voice_id="voice")
    with pytest.raises(ValidationError):
        ElevenLabsSettings(api_key="secret", voice_id="../escape")


def provider(handler):
    httpx = pytest.importorskip("httpx")
    return ElevenLabsVoice(ElevenLabsSettings(api_key="test-secret", voice_id="voice"), transport=httpx.MockTransport(handler))


def test_tts_exact_text_and_slowdown():
    httpx = pytest.importorskip("httpx")
    calls = []
    def handle(request):
        calls.append(request)
        body = json.loads(request.content)
        assert body["text"] == "Stay where you are."
        assert body["voice_settings"]["speed"] == 0.75
        assert request.headers["xi-api-key"] == "test-secret"
        assert request.url.path == "/v1/text-to-speech/voice"
        return httpx.Response(200, content=b"ID3audio", headers={"content-type":"audio/mpeg"})
    result = provider(handle).speak(Instruction(text="Stay where you are.", speech_rate=0.75))
    assert result.data == b"ID3audio" and len(calls) == 1


def test_transcription_upload_and_response():
    httpx = pytest.importorskip("httpx")
    def handle(request):
        assert request.url.path == "/v1/speech-to-text"
        assert b"recording.wav" in request.content
        assert b"scribe_v2" in request.content
        assert wav() in request.content
        return httpx.Response(200, json={"text":"No, nobody is injured.", "words":[]})
    assert provider(handle).transcribe(Recording(data=wav())).text == "No, nobody is injured."


@pytest.mark.parametrize("status", [401, 429, 500])
def test_provider_errors_redacted_and_not_retried(status):
    httpx = pytest.importorskip("httpx")
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(status, text="test-secret and private incident")
    with pytest.raises(VoiceError) as error:
        provider(handle).speak(Instruction(text="Hello"))
    assert "test-secret" not in str(error.value)
    assert "private incident" not in str(error.value)
    assert len(calls) == 1


def test_timeout_and_invalid_transcript_fallback():
    httpx = pytest.importorskip("httpx")
    def timeout(request):
        raise httpx.ReadTimeout("private incident")
    with pytest.raises(VoiceError):
        provider(timeout).speak(Instruction(text="Hello"))
    with pytest.raises(VoiceError):
        provider(lambda r: httpx.Response(200, json={"text":""})).transcribe(Recording(data=wav()))


class FakeProvider:
    def speak(self, instruction):
        return SpeechAudio(data=b"ID3audio")
    def transcribe(self, recording):
        return Transcript(text="Yes")


def test_consent_and_cached_playback():
    controller = VoiceController(FakeProvider())
    with pytest.raises(VoiceError):
        controller.speak(Instruction(text="Hello"))
    with pytest.raises(VoiceError):
        controller.transcribe(Recording(data=wav()))
    controller.allow("playback", True)
    controller.speak(Instruction(text="Hello"))
    controller.pending.result(timeout=2)
    controller.poll()
    assert controller.audio is not None
    controller.speak(Instruction(text="Hello"))
    assert not controller.busy
    controller.reset()
    assert not controller.playback_allowed and controller.audio is None


@pytest.mark.parametrize("change", ["context", "revoke", "reset"])
def test_stale_result_cannot_cross_turn_or_permission(change):
    controller = VoiceController(FakeProvider())
    controller.allow("microphone", True)
    future = Future()
    future.set_running_or_notify_cancel()
    controller.pending = future
    controller.pending_generation = controller.generation
    if change == "context":
        controller.set_context(("other-incident", 1))
    elif change == "revoke":
        controller.allow("microphone", False)
    else:
        controller.reset()
    assert controller.busy
    future.set_result(Transcript(text="Yes"))
    controller.poll()
    assert controller.transcript is None and not controller.busy


def test_voice_does_not_block_timers_or_submit_unreviewed_transcript():
    class Clock:
        time = 0
        def now(self): return self.time
    clock = Clock()
    coach = CollisionWorkflow(clock=clock)
    scene, first = coach.start()
    controller = VoiceController(FakeProvider())
    controller.pending = Future()
    controller.pending_generation = controller.generation
    clock.time = 8
    assert coach.poll(scene).text == first.text
    assert scene.unanswered_safety_turns == 1
    controller.pending.set_result(Transcript(text="Yes"))
    controller.poll()
    assert scene.unanswered_safety_turns == 1
    assert scene.status is SessionStatus.ACTIVE
    # Only the reviewed submission goes through the same deterministic guard.
    reply = coach.turn(scene, controller.transcript.text)
    assert reply.terminate and scene.status is SessionStatus.STOOD_DOWN
