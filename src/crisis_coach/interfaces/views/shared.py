import streamlit as st
from ...persistence.contracts import PersistenceError


def respond(reply):
    if reply is not None:
        st.session_state.messages.append(("assistant", reply.text))
        st.session_state.latest_reply = reply


def submit(text):
    try:
        if st.session_state.active_mode == "Practice":
            reply = st.session_state.practice.submit(text)
        else:
            reply = st.session_state.coach.turn(st.session_state.scene, text)
    except PersistenceError:
        st.error("Could not save this update. Reopen the incident before continuing.")
        st.stop()
    st.session_state.messages.append(("user", text))
    respond(reply)
    st.rerun()
