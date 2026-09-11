from __future__ import annotations

import streamlit as st

from crisis_coach.domains.collision import CollisionWorkflow


st.set_page_config(page_title="Crisis Coach", page_icon="🚨", layout="centered")
st.title("Crisis Coach")
st.caption("Collision prototype · one instruction at a time")

if "coach" not in st.session_state:
    st.session_state.coach = CollisionWorkflow()
    st.session_state.scene, first = st.session_state.coach.start("Dana Okoye")
    st.session_state.messages = [("assistant", first.text)]

for role, text in st.session_state.messages:
    with st.chat_message(role):
        st.write(text)

if not st.session_state.messages[-1][1].startswith("Stop."):
    if prompt := st.chat_input("Tell me what happened"):
        st.session_state.messages.append(("user", prompt))
        reply = st.session_state.coach.turn(st.session_state.scene, prompt)
        st.session_state.messages.append(("assistant", reply.text))
        st.rerun()
else:
    st.error("Session stood down. Call 911 now.")
