"""ElevenLabs REST boundary. No SDK, tracing, retries, or calls at import time."""
import json
import os
from time import monotonic
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from ...models.responses import Instruction
from .contracts import Recording, SpeechAudio, Transcript, VoiceError


class ElevenLabsSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    api_key: SecretStr
    voice_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    tts_model: str = Field(default="eleven_multilingual_v2", min_length=1, max_length=100)
    stt_model: str = Field(default="scribe_v2", min_length=1, max_length=100)
    timeout_seconds: float = Field(default=10, gt=0, le=30, allow_inf_nan=False)

    @field_validator("api_key")
    @classmethod
    def nonblank_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("API key must not be blank")
        return value

    @classmethod
    def from_environment(cls):
        key = os.getenv("ELEVENLABS_API_KEY")
        voice = os.getenv("ELEVENLABS_VOICE_ID")
        if not key or not voice:
            return None
        return cls(api_key=key, voice_id=voice,
                   tts_model=os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2"),
                   stt_model=os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2"))


class ElevenLabsVoice:
    def __init__(self, settings: ElevenLabsSettings, transport=None):
        self.settings = settings
        self._transport = transport

    def _request(self, path, limit, **kwargs):
        try:
            import httpx
        except ImportError:
            raise VoiceError('Install voice support with pip install -e ".[voice]"') from None
        try:
            started = monotonic()
            with httpx.Client(timeout=self.settings.timeout_seconds, follow_redirects=False,
                              transport=self._transport) as client:
                with client.stream("POST", "https://api.elevenlabs.io/v1/" + path,
                                   headers={"xi-api-key": self.settings.api_key.get_secret_value()}, **kwargs) as response:
                    response.raise_for_status()
                    result = bytearray()
                    for chunk in response.iter_bytes():
                        result.extend(chunk)
                        if len(result) > limit or monotonic() - started > self.settings.timeout_seconds:
                            raise VoiceError("Voice response exceeded its size or time limit. Continue using text.")
                    return bytes(result), response.headers.get("content-type", "").split(";")[0]
        except VoiceError:
            raise
        except Exception:
            raise VoiceError("ElevenLabs is unavailable. Check voice configuration or credits; continue using text.") from None

    def speak(self, instruction: Instruction) -> SpeechAudio:
        if len(instruction.text) > 5000:
            raise VoiceError("This response is too long for voice playback. Read the text instead.")
        data, media = self._request("text-to-speech/" + self.settings.voice_id, 5 * 1024 * 1024,
            params={"output_format": "mp3_44100_128"},
            json={"text": instruction.text, "model_id": self.settings.tts_model,
                  "voice_settings": {"speed": max(0.7, instruction.speech_rate)}})
        if media != "audio/mpeg" or not data:
            raise VoiceError("ElevenLabs returned no playable speech. Read the text instead.")
        return SpeechAudio(data=data)

    def transcribe(self, recording: Recording) -> Transcript:
        data, _ = self._request("speech-to-text", 1024 * 1024,
            data={"model_id": self.settings.stt_model, "language_code": "en",
                  "tag_audio_events": "false", "diarize": "false", "webhook": "false"},
            files={"file": ("recording.wav", recording.data, "audio/wav")})
        try:
            return Transcript(text=json.loads(data)["text"])
        except (ValueError, KeyError, TypeError):
            raise VoiceError("No usable transcript was returned. Try a short recording or type your answer.") from None


def build_voice_provider():
    try:
        settings = ElevenLabsSettings.from_environment()
        if settings is None:
            return None
        import httpx  # noqa: F401 -- optional dependency availability, no network
        return ElevenLabsVoice(settings)
    except (ImportError, ValueError):
        return None
