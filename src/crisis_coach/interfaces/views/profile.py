import streamlit as st
from ...models.profile import Profile
from ...persistence.profiles import ProfileRepository
from ...persistence.contracts import PersistenceError


def render_profile():
    st.subheader("Your profile")
    st.caption("Optional preparation. You can start an incident without completing this form. Details apply to new incidents; source lookup still needs explicit context.")
    if st.session_state.active_mode == "Practice":
        st.info("Practice uses a synthetic profile. Your saved profile is not read or changed.")
        st.write(st.session_state.scene.profile.model_dump(exclude={"revision"}))
        return
    repo = ProfileRepository(st.session_state.data_root / "profile.sqlite3")
    try:
        if "profile_draft" not in st.session_state:
            st.session_state.profile_draft = repo.load()
    except PersistenceError:
        st.error("Profile storage is unavailable. Incident safety checks remain available.")
        return
    profile = st.session_state.profile_draft
    with st.form("profile_form"):
        fields = {}
        for key,label in [("name","Name"),("vehicle","Vehicle"),("registration","Registration"),("insurer","Insurer"),("policy_id","Policy identifier"),("trusted_contact","Trusted contact"),("contact_phone","Contact phone")]:
            fields[key] = st.text_input(label, value=getattr(profile,key), max_chars={"vehicle":200,"registration":40,"contact_phone":80}.get(key,120), key=f"profile_{key}")
        save = st.form_submit_button("Save profile")
    if save:
        from pydantic import ValidationError
        try:
            saved = repo.save(Profile(**fields, revision=profile.revision))
        except (PersistenceError, ValidationError) as exc:
            st.error(str(exc))
        else:
            st.session_state.profile_draft = saved
            st.success("Profile saved locally. New incidents will include this snapshot.")
    if st.button("Reload saved profile"):
        st.session_state.pop("profile_draft",None)
        for key in fields: st.session_state.pop(f"profile_{key}",None)
        st.rerun()
