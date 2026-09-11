import streamlit as st
from ...models.events import ReportEvent
from ...persistence.contracts import PersistenceError
from ...reporting.evidence_pack import read_export
from ...tools.contracts import ToolError
from .presentation import actionable, ledger_rows
from .shared import respond


def render_report():
    scene, coach = st.session_state.scene, st.session_state.coach
    st.subheader("Evidence pack")
    st.caption("Review originals and gaps before exporting. Stored files and user reports are shown separately.")
    rows = ledger_rows(coach,scene)
    if rows: st.dataframe(rows, hide_index=True, width="stretch")
    else: st.info("No evidence recorded yet.")
    for key,record in scene.evidence.items():
        photos = [ref for ref in record.attachments if ref.media_type.startswith("image/")]
        if photos:
            with st.expander("Stored photos · " + key.replace("_"," ")):
                from ...persistence.attachments import AttachmentStore
                store = AttachmentStore(st.session_state.data_root / "attachments")
                for reference in photos:
                    try:
                        data = store.read(scene.incident_id,reference)
                        st.image(data,caption="Stored original · review quality before sharing",width="stretch")
                    except (ToolError, OSError, ValueError):
                        st.warning("This attachment could not be displayed. Export will identify missing or unsupported images.")
        if record.original_text:
            with st.expander("Original text · " + key.replace("_"," ")):
                st.text(record.original_text)
    if scene.knowledge_answers:
        with st.expander("Recorded source lookups"):
            for answer in scene.knowledge_answers:
                st.write(answer.question)
                st.write(answer.message)
                for source in answer.citations:
                    st.text(f"{'SYNTHETIC · ' if source.synthetic else ''}{source.title}, {source.section}: {source.text}")
    allowed = actionable(coach,scene)
    if st.button("Build evidence pack", disabled=not allowed, key="build_pack"):
        try: respond(coach.handle_event(scene, ReportEvent()))
        except PersistenceError:
            st.error("Could not save export. Reopen the incident before continuing.")
            return
        st.rerun()
    if not allowed: st.caption("Finish safety checks and resume before building a pack.")
    if scene.exports:
        latest = scene.exports[-1]
        try: data = read_export(st.session_state.data_root / "exports",scene.incident_id,latest)
        except ToolError as exc: st.error(str(exc))
        else:
            st.caption(f"Snapshot revision {latest.incident_revision} · current revision {scene.revision}. Export again after additions.")
            st.download_button("Download evidence pack",data=data,file_name="crisis-coach-evidence.docx",mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",key="download_pack")
