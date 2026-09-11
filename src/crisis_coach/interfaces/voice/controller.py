"""One background request per browser session; never mutates the workflow."""
from concurrent.futures import ThreadPoolExecutor
from .contracts import Recording, SpeechAudio, Transcript, VoiceError, VoiceProvider
from ...models.responses import Instruction


class VoiceController:
    def __init__(self, provider: VoiceProvider):
        self.provider = provider
        self.playback_allowed = False
        self.microphone_allowed = False
        self.context = None
        self.generation = 0
        self.pending = None
        self.pending_generation = None
        self.audio: SpeechAudio | None = None
        self.transcript: Transcript | None = None
        self.error: str | None = None

    def invalidate(self):
        self.generation += 1
        self.audio = self.transcript = self.error = None
        # Running requests cannot be recalled. Keep the slot occupied until done.
        if self.pending is not None:
            self.pending.cancel()

    def reset(self):
        self.playback_allowed = self.microphone_allowed = False
        self.invalidate()

    def set_context(self, context):
        if context != self.context:
            self.context = context
            self.invalidate()

    def allow(self, capability, enabled):
        if capability not in ("playback", "microphone"):
            raise ValueError("Unknown voice capability")
        setattr(self, capability + "_allowed", enabled)
        self.invalidate()

    @property
    def busy(self):
        return self.pending is not None

    def _start(self, operation, value):
        if self.busy:
            raise VoiceError("A voice request is still finishing. You can continue using text.")
        self.error = None
        self.pending_generation = self.generation
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crisis-voice")
        self.pending = executor.submit(operation, value)
        executor.shutdown(wait=False)

    def speak(self, instruction: Instruction):
        if not self.playback_allowed:
            raise VoiceError("Enable ElevenLabs playback first.")
        if self.audio is None:
            self._start(self.provider.speak, instruction)

    def transcribe(self, recording: Recording):
        if not self.microphone_allowed:
            raise VoiceError("Enable ElevenLabs transcription first.")
        if self.busy:
            raise VoiceError("A voice request is still finishing. You can continue using text.")
        self.invalidate()
        self._start(self.provider.transcribe, recording)

    def poll(self):
        if self.pending is None or not self.pending.done():
            return
        future, self.pending = self.pending, None
        if self.pending_generation != self.generation:
            return
        try:
            result = future.result()
            if isinstance(result, SpeechAudio):
                self.audio = result
            elif isinstance(result, Transcript):
                self.transcript = result
            else:
                raise VoiceError("Voice returned an invalid result. Continue using text.")
        except VoiceError as exc:
            self.error = str(exc)
        except Exception:
            self.error = "Voice is unavailable. Continue using text."
