from __future__ import annotations

import streamlit as st
from pathlib import Path
import tempfile
from crisis_coach.models.events import CaptureEvent, ReportEvent, ContextEvent, AIConsentEvent

from crisis_coach.bootstrap import build_coach, build_repository
from crisis_coach.persistence.contracts import PersistenceError
from crisis_coach.models import SessionStatus, SafetyGate
from crisis_coach.interfaces.voice.view import render_voice, reset_voice


st.set_page_config(page_title="Crisis Coach", page_icon="🚨", layout="centered")
st.title("Crisis Coach")
st.caption("Collision prototype · one instruction at a time")

if "coach" not in st.session_state:
    try:
        coach = build_coach()
        scene, first = coach.start("Dana Okoye")
    except PersistenceError:
        st.error("Cannot open incident storage.")
        st.stop()
    st.session_state.coach = coach
    st.session_state.scene = scene
    st.session_state.messages = [("assistant", first.text)]
    st.session_state.latest_reply = first

try:
    incidents = build_repository().list_incidents()
    selection = st.sidebar.selectbox("Saved incidents", [item.incident_id for item in incidents])
    if st.sidebar.button("Open selected incident") and selection:
        st.session_state.scene, first = st.session_state.coach.reopen(selection)
        st.session_state.messages = [("assistant", first.text)]
        st.session_state.latest_reply = first
        reset_voice()
        st.rerun()
    if st.sidebar.button("New incident"):
        st.session_state.scene, first = st.session_state.coach.start()
        st.session_state.messages = [("assistant", first.text)]
        st.session_state.latest_reply = first
        reset_voice()
        st.rerun()
except PersistenceError:
    st.error("Incident storage is unavailable. Reopen the app when storage is available.")
    st.stop()

for role, text in st.session_state.messages:
    with st.chat_message(role):
        st.write(text)

if st.session_state.scene.status is not SessionStatus.STOOD_DOWN or st.session_state.scene.safety_gate is SafetyGate.MEDICAL_REENTRY:
    if prompt := st.chat_input("Tell me what happened"):
        st.session_state.messages.append(("user", prompt))
        try:
            reply = st.session_state.coach.turn(st.session_state.scene, prompt)
        except PersistenceError:
            st.error("Could not save this update. Reopen the incident before continuing.")
            st.stop()
        st.session_state.messages.append(("assistant", reply.text))
        st.session_state.latest_reply = reply
        st.rerun()
else:
    st.error("Session stood down. Call 911 now.")

    if st.button("Reopen this incident"):
        try:
            reply = st.session_state.coach.turn(st.session_state.scene, "")
            reset_voice()
        except PersistenceError:
            st.error("Cannot reopen this incident while storage is unavailable.")
            st.stop()
        st.session_state.messages.append(("assistant", reply.text))
        st.session_state.latest_reply = reply
        st.rerun()


# Uploads are staged only long enough for the executor to copy them into the
# immutable attachment store. The interface never edits the evidence ledger.
scene = st.session_state.scene
if scene.status is SessionStatus.ACTIVE and st.session_state.coach.pack.is_cleared(scene):
    if scene.current_evidence_id:
        item_id = scene.current_evidence_id
        capture_tool = st.session_state.coach.pack.capture_tool(scene, item_id)
        st.caption("Record the requested evidence below. Uploaded photos are not yet quality-verified.")
        if capture_tool == "capture_photo":
            uploaded = st.file_uploader("Choose a photo", type=["png", "jpg", "jpeg"], key=f"photo_{scene.incident_id}_{item_id}")
            if uploaded is not None and st.button("Save photo", key=f"save_{item_id}"):
                if uploaded.size > 20 * 1024 * 1024:
                    st.error("Choose a file smaller than 20 MiB.")
                else:
                    try:
                        with tempfile.TemporaryDirectory(prefix="crisis-upload-") as staging:
                            source = Path(staging) / "upload"
                            source.write_bytes(uploaded.getvalue())
                            reply = st.session_state.coach.handle_event(scene, CaptureEvent(item_id=item_id, tool="capture_photo", arguments={"source_path": str(source)}))
                    except (PersistenceError, OSError):
                        st.error("Could not save this photo. Reopen the incident and try again.")
                        st.stop()
                    if reply is not None:
                        st.session_state.messages.append(("assistant", reply.text))
                        st.session_state.latest_reply = reply
                    st.rerun()
        elif capture_tool == "record_statement":
            statement = st.text_area("Record the details in your own words", max_chars=20000, key=f"text_{scene.incident_id}_{item_id}")
            if st.button("Save text", key=f"save_{item_id}") and statement.strip():
                try:
                    reply = st.session_state.coach.handle_event(scene, CaptureEvent(item_id=item_id, tool="record_statement", arguments={"text": statement}))
                except PersistenceError:
                    st.error("Could not save this text. Reopen the incident and try again.")
                    st.stop()
                if reply is not None:
                    st.session_state.messages.append(("assistant", reply.text))
                    st.session_state.latest_reply = reply
                st.rerun()


if scene.status is SessionStatus.ACTIVE and st.session_state.coach.pack.is_cleared(scene):
    if st.button("Build evidence pack"):
        try:
            reply = st.session_state.coach.handle_event(scene, ReportEvent())
        except PersistenceError:
            st.error("Could not save the export record. Reopen the incident and try again.")
            st.stop()
        if reply is not None:
            st.session_state.messages.append(("assistant", reply.text))
            st.session_state.latest_reply = reply
        st.rerun()
    if scene.exports:
        from crisis_coach.config import AppSettings
        from crisis_coach.reporting.evidence_pack import read_export
        from crisis_coach.tools.contracts import ToolError
        latest = scene.exports[-1]
        try:
            export_data = read_export(AppSettings().data_dir / "exports", scene.incident_id, latest)
        except ToolError as exc:
            st.error(str(exc))
        else:
            st.caption(f"Export snapshot of revision {latest.incident_revision}; later additions require a new export.")
            st.download_button("Download evidence pack", data=export_data, file_name="crisis-coach-evidence.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


if scene.status is SessionStatus.ACTIVE and st.session_state.coach.pack.is_cleared(scene):
    from crisis_coach.models.knowledge import KnowledgeContext
    with st.expander("Policy and jurisdiction for source lookup"):
        st.caption("Use identifiers from your reviewed local source files. Demo mode uses fictional sources only.")
        with st.form("knowledge_context"):
            policy_id = st.text_input("Policy identifier", value=scene.knowledge_context.policy_id or "")
            jurisdiction = st.text_input("Jurisdiction identifier", value=scene.knowledge_context.jurisdiction or "")
            reference_date = st.date_input("Incident reference date", value=scene.knowledge_context.reference_date)
            synthetic = st.checkbox("Allow synthetic demonstration sources", value=scene.knowledge_context.allow_synthetic)
            update_context = st.form_submit_button("Apply source context")
        if update_context:
            try:
                reply = st.session_state.coach.handle_event(scene, ContextEvent(context=KnowledgeContext(policy_id=policy_id.strip() or None, jurisdiction=jurisdiction.strip() or None, reference_date=reference_date, allow_synthetic=synthetic)))
            except PersistenceError:
                st.error("Could not save source context.")
                st.stop()
            if reply is not None:
                st.session_state.messages.append(("assistant", reply.text))
                st.session_state.latest_reply = reply
            st.rerun()


if scene.status is SessionStatus.ACTIVE and st.session_state.coach.pack.is_cleared(scene):
    with st.expander("Optional AI sharing"):
        st.caption("Enabling a capability sends new eligible text or photos to your configured provider and may use paid credits. Permission resets when reopening.")
        for capability, enabled in (("text", scene.ai_text_allowed), ("images", scene.ai_images_allowed)):
            specialist = getattr(st.session_state.coach.pack, "interpreter", None) if capability == "text" else st.session_state.coach.photo_reviewer
            label = getattr(specialist, "provider_label", "not configured")
            if st.button(f"{'Disable' if enabled else 'Enable'} AI {capability} ({label})", key=f"ai_{capability}"):
                try:
                    reply = st.session_state.coach.handle_event(scene, AIConsentEvent(capability=capability, allowed=not enabled))
                except PersistenceError:
                    st.error("Could not save AI permission.")
                    st.stop()
                if reply is not None:
                    st.session_state.messages.append(("assistant", reply.text))
                    st.session_state.latest_reply = reply
                st.rerun()


@st.fragment(run_every="1s")
def check_silence():
    try:
        reply = st.session_state.coach.poll(st.session_state.scene)
    except PersistenceError:
        st.error("Could not save this update. Reopen the incident before continuing.")
        st.stop()
    if reply is not None:
        st.session_state.messages.append(("assistant", reply.text))
        st.session_state.latest_reply = reply
        st.rerun()

check_silence()
render_voice()
