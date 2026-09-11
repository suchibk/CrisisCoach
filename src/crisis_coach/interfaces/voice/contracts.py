"""Validated, transient voice data; recordings are not incident attachments."""
from io import BytesIO
from typing import Literal, Protocol
import wave
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ...models.responses import Instruction


class VoiceError(RuntimeError):
    """Safe user-facing voice failure, without provider payloads or credentials."""


class Recording(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    data: bytes = Field(min_length=1, max_length=2 * 1024 * 1024, repr=False)

    @field_validator("data")
    @classmethod
    def validate_wav(cls, data: bytes) -> bytes:
        try:
            with wave.open(BytesIO(data), "rb") as audio:
                frames, rate = audio.getnframes(), audio.getframerate()
                if not 0.1 <= frames / rate <= 30:
                    raise ValueError("Record between 0.1 and 30 seconds")
                if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
                    raise ValueError("Use a mono 16-bit PCM WAV recording")
                if len(audio.readframes(frames)) != frames * 2:
                    raise ValueError("Recording is truncated")
        except (wave.Error, EOFError, ZeroDivisionError) as exc:
            raise ValueError("Use a valid PCM WAV recording") from exc
        return data


class Transcript(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("No speech recognized")
        return value


class SpeechAudio(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    data: bytes = Field(min_length=1, max_length=5 * 1024 * 1024, repr=False)
    media_type: Literal["audio/mpeg"] = "audio/mpeg"


class VoiceProvider(Protocol):
    def speak(self, instruction: Instruction) -> SpeechAudio: ...
    def transcribe(self, recording: Recording) -> Transcript: ...
