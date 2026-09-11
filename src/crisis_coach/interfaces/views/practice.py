import streamlit as st
from ...models import SafetyGate, SessionStatus
from .shared import submit, respond
from .presentation import actionable, ledger_rows


def render_practice():
    runtime = st.session_state.practice
    scene,coach = runtime.scene,runtime.coach
    st.subheader("Practice prompts")
    st.caption("Suggested inputs use the real workflow. Photos below are labelled local simulations.")
    if scene.status is SessionStatus.STOOD_DOWN:
        options = ["I am away from the danger and safe now"] if scene.safety_gate == SafetyGate.DANGER_REENTRY else []
    elif scene.safety_gate == SafetyGate.USER_INJURY:
        options = ["No, I'm fine — shaken, but fine", "My neck hurts"]
    elif scene.safety_gate == SafetyGate.OTHER_INJURY:
        options = ["No, he's out of his car and looks okay"]
    elif scene.safety_gate == SafetyGate.SAFE_LOCATION:
        options = ["Yes, I'm on the kerb"]
    else:
        options = ["He's getting back in his car", "There's a witness walking away", "Sorry — I think it was my fault", "Do I need to call the police?", "He's shouting at me", "My neck hurts"]
    for index,option in enumerate(options):
        if st.button(option,key=f"practice_prompt_{index}"): submit(option)
    if actionable(coach,scene) and scene.current_evidence_id and coach.pack.capture_tool(scene,scene.current_evidence_id) == "capture_photo":
        for verdict,label in [("retake","Simulate rejected photo"),("usable","Simulate usable photo")]:
            if st.button(label,key=f"practice_photo_{verdict}"):
                respond(runtime.capture(verdict))
                st.rerun()
    if st.button("Advance practice clock 8 seconds",key="practice_clock"):
        runtime.clock.advance(8)
        respond(coach.poll(scene))
        st.rerun()
    st.caption(f"Practice clock: {runtime.clock.now():.0f}s. Time advances only with this control.")
    with st.expander("How this is unfolding",expanded=True):
        if not scene.trace: st.write("Session opened · safety check")
        with st.container(height=260):
            for entry in scene.trace[-12:]:
                st.write(f"{entry.event_kind.replace('_',' ')} · {entry.status.replace('_',' ')} · {entry.gate.replace('_',' ')}")
                st.caption(" → ".join(entry.route))
        if scene.status is SessionStatus.STOOD_DOWN:
            st.warning("Collection is stopped. Earlier decisions are history, not active instructions.")
        elif scene.last_decision:
            st.write("Current priority: " + (scene.last_decision.selected_id or "No pending tasks"))
            st.dataframe([{"Item":c.item_id,"Score":round(c.score,3),"Seconds remaining at decision":f"{c.seconds_remaining:.0f}s" if c.seconds_remaining is not None else "Unknown","Reason":c.reason} for c in scene.last_decision.candidates],hide_index=True,width="stretch")
    with st.expander("Scene state"):
        st.write("Gate: " + str(scene.safety_gate))
        rows=ledger_rows(coach,scene)
        if rows: st.dataframe(rows,hide_index=True,width="stretch")
        st.caption("Estimated deadlines do not establish that a person has actually left.")
