"""Explicit, push-to-record voice controls over the existing text workflow."""
import streamlit as st
from pydantic import ValidationError
from .contracts import Recording, VoiceError
from .controller import VoiceController
from .elevenlabs import build_voice_provider
from ...models import SessionStatus, SafetyGate
from ...persistence.contracts import PersistenceError


def reset_voice():
    controller = st.session_state.get("voice_controller")
    if controller is not None:
        controller.reset()


@st.fragment(run_every="1s")
def render_voice():
    with st.expander("ElevenLabs voice"):
        controller = st.session_state.get("voice_controller")
        if controller is None:
            provider = build_voice_provider()
            if provider is None:
                st.caption("Voice is optional. Configure ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID and install the voice extra, then restart the app.")
                return
            controller = VoiceController(provider)
            st.session_state.voice_controller = controller
        scene = st.session_state.scene
        controller.set_context((scene.incident_id, len(st.session_state.messages)))
        controller.poll()
        st.caption("Playback sends the displayed coach response to ElevenLabs. Transcription sends your recording. Charges and ElevenLabs retention policies apply. Permissions reset when you open or start an incident.")
        for capability, label in (("playback", "speech playback"), ("microphone", "recording transcription")):
            enabled = getattr(controller, capability + "_allowed")
            if st.button(f"{'Disable' if enabled else 'Enable'} {label}", key=f"voice_allow_{capability}"):
                controller.allow(capability, not enabled)
                st.rerun()
        token = f"{scene.incident_id}_{controller.generation}"
        if controller.error:
            st.warning(controller.error)
        if controller.busy:
            st.caption("Voice request in progress. Text controls and safety timers remain active.")
        if controller.playback_allowed:
            instruction = st.session_state.get("latest_reply", scene.last_instruction)
            if instruction and st.button("Prepare spoken response", disabled=controller.busy, key="voice_speak"):
                try:
                    controller.speak(instruction)
                except VoiceError as exc:
                    st.warning(str(exc))
            if controller.audio:
                st.audio(controller.audio.data, format=controller.audio.media_type)
                st.caption("Use the player to play, pause, or replay without another API call.")
        can_answer = scene.status is not SessionStatus.STOOD_DOWN or scene.safety_gate is SafetyGate.MEDICAL_REENTRY
        if controller.microphone_allowed and can_answer:
            recording = st.audio_input("Record a short answer (maximum 30 seconds)", key=f"voice_record_{token}")
            if st.button("Send recording to ElevenLabs", disabled=recording is None or controller.busy, key="voice_transcribe"):
                try:
                    controller.transcribe(Recording(data=recording.getvalue()))
                except ValidationError:
                    st.warning("Use a mono PCM WAV recording between 0.1 and 30 seconds, smaller than 2 MiB.")
                except VoiceError as exc:
                    st.warning(str(exc))
            if controller.transcript is not None:
                with st.form(f"voice_confirm_{token}"):
                    reviewed = st.text_area("Check the transcript before sending", value=controller.transcript.text, max_chars=2000)
                    send = st.form_submit_button("Send reviewed answer")
                if send and reviewed.strip():
                    try:
                        reply = st.session_state.coach.turn(scene, reviewed)
                    except PersistenceError:
                        controller.invalidate()
                        st.error("Could not save your answer. Reopen the incident before continuing.")
                        st.stop()
                    st.session_state.messages.extend([("user", reviewed), ("assistant", reply.text)])
                    st.session_state.latest_reply = reply
                    controller.invalidate()
                    st.rerun()
        st.caption("Recordings are transient and are not evidence attachments. Only a submitted, reviewed answer enters the incident record. Voice never submits an answer automatically.")
