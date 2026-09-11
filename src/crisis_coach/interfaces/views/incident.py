import streamlit as st
from ...models import SessionStatus, SafetyGate
from .shared import submit
from .presentation import actionable, progress
from .collection import render_capture, render_context, render_sources, render_ai


def render_incident():
    scene,coach=st.session_state.scene,st.session_state.coach
    with st.container(border=True,key="coach_card"):
        st.caption("ONE STEP AT A TIME")
        if scene.status is SessionStatus.STOOD_DOWN:
            st.error("Collection stopped")
            st.write(st.session_state.latest_reply.text)
            if scene.safety_gate not in (SafetyGate.MEDICAL_REENTRY,SafetyGate.DANGER_REENTRY):
                if st.button("Reopen this incident",key="reopen_safety"): submit("")
        elif scene.status is SessionStatus.STOPPED:
            st.warning("Paused")
            st.write("Your current task is saved. Resume when you are ready.")
        else:
            st.subheader(scene.last_instruction.text if scene.last_instruction else "Safety check")
            st.caption("Safety checks" if not coach.pack.is_cleared(scene) else "Evidence collection")
    controls=st.columns(3)
    with controls[0]:
        command="resume" if scene.status is SessionStatus.STOPPED else "pause"
        if st.button(command.title(),disabled=scene.status is SessionStatus.STOOD_DOWN,key="control_pause",width="stretch"): submit(command)
    with controls[1]:
        if st.button("Repeat",disabled=scene.status is not SessionStatus.ACTIVE,key="control_repeat",width="stretch"): submit("repeat")
    with controls[2]:
        if st.button("Slow down",disabled=scene.status is not SessionStatus.ACTIVE,key="control_slow",width="stretch"): submit("slow down")
    if scene.evidence:
        counts=progress(coach,scene)
        st.caption(" · ".join(f"{label}: {value}" for label,value in counts.items()))
        st.caption("Stored counts include retained retakes; they do not measure verification or export completeness.")
    with st.expander("Conversation",expanded=True):
        with st.container(height=280):
            for role,text in st.session_state.messages[-12:]:
                with st.chat_message(role): st.write(text)
    if actionable(coach,scene):
        render_capture(scene)
        render_context(scene)
        render_sources(scene)
        if st.session_state.active_mode != "Practice": render_ai(scene)
    can_answer=scene.status is not SessionStatus.STOOD_DOWN or scene.safety_gate in (SafetyGate.MEDICAL_REENTRY,SafetyGate.DANGER_REENTRY)
    if prompt:=st.chat_input("Tell me what happened",disabled=not can_answer): submit(prompt)
