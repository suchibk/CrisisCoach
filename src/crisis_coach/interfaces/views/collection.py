"""Capture and context views use typed events on the shared workflow."""
import streamlit as st
from pathlib import Path
import tempfile
from crisis_coach.models.events import CaptureEvent, ContextEvent, AIConsentEvent
from crisis_coach.persistence.contracts import PersistenceError

def render_capture(scene):
    if scene.current_evidence_id:
        item_id = scene.current_evidence_id
        capture_tool = st.session_state.coach.pack.capture_tool(scene, item_id)
        st.caption("Save original evidence here. Any quality assessment is labelled separately.")
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

def render_sources(scene):
    from crisis_coach.models.knowledge import KnowledgeContext
    with st.expander("Policy and jurisdiction for source lookup"):
        st.caption("Use identifiers from your reviewed local source files. Demo mode uses fictional sources only.")
        with st.form(f"knowledge_context_{scene.incident_id}"):
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

def render_ai(scene):
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

def render_context(scene):
    from crisis_coach.models.incident_context import IncidentContext
    from crisis_coach.models.events import IncidentContextEvent
    from pydantic import ValidationError
    with st.expander("Incident time, location and weather"):
        st.caption("Enter what you know. Leave unknown details blank. Saving replaces these details.")
        with st.form(f"incident_context_{scene.incident_id}"):
            occurred = st.text_input("Incident time with UTC offset (e.g. 2026-09-11T14:30:00-04:00)", value=scene.incident_context.occurred_at.isoformat() if scene.incident_context.occurred_at else "")
            location = st.text_input("Location", value=scene.incident_context.location or "", max_chars=1000)
            weather = st.text_input("Observed weather", value=scene.incident_context.weather or "", max_chars=1000)
            save_context = st.form_submit_button("Save incident details")
        if save_context:
            try:
                context = IncidentContext(occurred_at=occurred.strip() or None, location=location.strip() or None, weather=weather.strip() or None)
                reply = st.session_state.coach.handle_event(scene, IncidentContextEvent(context=context))
            except ValidationError:
                st.error("Use an ISO date and time with a UTC offset, or leave the time blank.")
            except PersistenceError:
                st.error("Could not save incident details. Reopen the incident before continuing.")
            else:
                if reply is not None:
                    st.session_state.messages.append(("assistant", reply.text))
                    st.session_state.latest_reply = reply
                st.rerun()


