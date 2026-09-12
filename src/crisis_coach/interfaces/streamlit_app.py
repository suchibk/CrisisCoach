"""Streamlit shell; all incident mutations go through WorkflowEngine."""
from pathlib import Path
import streamlit as st
from crisis_coach.bootstrap import build_coach, build_repository
from crisis_coach.config import AppSettings
from crisis_coach.models.profile import Profile
from crisis_coach.persistence.profiles import ProfileRepository
from crisis_coach.persistence.contracts import PersistenceError
from crisis_coach.practice.runtime import PracticeRuntime, SCENARIOS
from crisis_coach.interfaces.voice.view import render_voice, reset_voice
from crisis_coach.interfaces.views.appearance import render_appearance
from crisis_coach.interfaces.views.incident import render_incident
from crisis_coach.interfaces.views.practice import render_practice
from crisis_coach.interfaces.views.profile import render_profile
from crisis_coach.interfaces.views.report import render_report
from crisis_coach.interfaces.views.shared import respond

st.set_page_config(page_title="Crisis Coach",page_icon="🧭",layout="wide")


def assign(coach,scene,reply,root):
    st.session_state.coach=coach
    st.session_state.scene=scene
    st.session_state.latest_reply=reply
    st.session_state.messages=[("assistant",reply.text)]
    st.session_state.data_root=root
    reset_voice()
    st.session_state.pop("voice_controller",None)


def saved_profile():
    try: return ProfileRepository(AppSettings().data_dir / "profile.sqlite3").load()
    except PersistenceError:
        st.sidebar.warning("Profile unavailable. You can still start an incident.")
        return Profile()


mode=st.sidebar.radio("Mode",["Live incident","Practice"],key="mode")
if "active_mode" not in st.session_state:
    st.session_state.active_mode=mode
    if mode == "Practice":
        runtime=PracticeRuntime()
        st.session_state.practice=runtime
        assign(runtime.coach,runtime.scene,runtime.first,runtime.root)
    else:
        try:
            coach=build_coach()
            profile=saved_profile()
            scene,first=coach.start(profile.name or "Incident owner",profile=profile)
            assign(coach,scene,first,AppSettings().data_dir)
        except PersistenceError:
            st.error("Cannot open incident storage.")
            st.stop()

if mode != st.session_state.active_mode:
    if mode == "Practice":
        st.session_state.live_session=(st.session_state.coach,st.session_state.scene.incident_id)
        runtime=PracticeRuntime()
        st.session_state.practice=runtime
        assign(runtime.coach,runtime.scene,runtime.first,runtime.root)
    else:
        try:
            if "live_session" in st.session_state:
                coach,incident_id=st.session_state.live_session
                scene,first=coach.reopen(incident_id)
            else:
                coach=build_coach()
                profile=saved_profile()
                scene,first=coach.start(profile.name or "Incident owner",profile=profile)
        except PersistenceError:
            st.error("Cannot restore live storage. Your practice session remains available.")
            st.stop()
        assign(coach,scene,first,AppSettings().data_dir)
        st.session_state.practice.close()
        del st.session_state.practice
    st.session_state.active_mode=mode
    st.rerun()

render_appearance()
view=st.sidebar.radio("View",["Incident","Evidence pack","Profile"],key="view")
if mode == "Practice":
    selected=st.sidebar.selectbox("Practice scenario",list(SCENARIOS),key="practice_scenario")
    if st.sidebar.button("Start / reset practice",key="reset_practice"):
        replacement=PracticeRuntime(selected)
        st.session_state.practice.close()
        st.session_state.practice=replacement
        assign(replacement.coach,replacement.scene,replacement.first,replacement.root)
        st.rerun()
    st.sidebar.caption("Active scenario: " + st.session_state.practice.scenario)
else:
    try:
        incidents=build_repository().list_incidents()
        selected=st.sidebar.selectbox("Saved incidents",[i.incident_id for i in incidents])
        if st.sidebar.button("Open selected incident") and selected:
            scene,first=st.session_state.coach.reopen(selected)
            assign(st.session_state.coach,scene,first,AppSettings().data_dir)
            st.rerun()
        if st.sidebar.button("New incident"):
            profile=saved_profile()
            scene,first=st.session_state.coach.start(profile.name or "Incident owner",profile=profile)
            assign(st.session_state.coach,scene,first,AppSettings().data_dir)
            st.rerun()
    except PersistenceError:
        st.sidebar.error("Saved incidents are unavailable. Reopen the app to retry.")

st.title("Crisis Coach")
if mode == "Practice":
    st.info("PRACTICE · Synthetic scenario · Temporary storage · No external AI or voice calls")
else:
    st.caption("Collision support · Saved locally · One instruction at a time")

if view == "Profile": render_profile()
elif view == "Evidence pack": render_report()
elif mode == "Practice":
    main,details=st.columns([1.5,1],gap="large")
    with main: render_incident()
    with details: render_practice()
else:
    render_incident()


@st.fragment(run_every="1s")
def check_silence():
    if st.session_state.active_mode == "Practice": return
    voice = st.session_state.get("voice_controller")
    # audio_input does not report recording start to Python. While microphone
    # input is enabled, wait for the reviewed answer instead of resetting the
    # recorder or discarding transcription on an automatic timer message.
    if voice is not None and voice.microphone_allowed:
        return
    try: reply=st.session_state.coach.poll(st.session_state.scene)
    except PersistenceError:
        st.error("Could not save the timer update. Reopen the incident.")
        return
    if reply is not None:
        respond(reply)
        st.rerun()

check_silence()
if mode != "Practice": render_voice()
