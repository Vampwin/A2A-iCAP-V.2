import html
import streamlit as st

from utils.ui_style import apply_poster_style, render_glossary_sidebar
from utils.auth import (
    require_login,
    render_sidebar_user,
    update_profile,
    change_password,
    ROLE_OPTIONS,
)
from utils.wizard import render_wizard_sidebar


sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar()
render_glossary_sidebar()


st.title("👤 Account Settings")

metadata = st.session_state.get("sb_user_metadata", {}) or {}
email = st.session_state.get("sb_user_email", "")

st.markdown(
    f'<p class="small-note">Signed in as <b>{html.escape(email)}</b></p>',
    unsafe_allow_html=True,
)

st.subheader("Profile Information")
with st.form("profile_form"):
    full_name = st.text_input("Full name", value=metadata.get("full_name", ""))
    affiliation = st.text_input(
        "Affiliation / Organization", value=metadata.get("affiliation", "")
    )
    current_role = metadata.get("role", ROLE_OPTIONS[0])
    role = st.selectbox(
        "Role",
        ROLE_OPTIONS,
        index=ROLE_OPTIONS.index(current_role) if current_role in ROLE_OPTIONS else 0,
    )
    save_profile = st.form_submit_button("Save Changes", use_container_width=True)

if save_profile:
    if not full_name or not affiliation:
        st.error("Please fill in all fields.")
    else:
        try:
            update_profile(sb, {
                "full_name": full_name.strip(),
                "affiliation": affiliation.strip(),
                "role": role,
            })
            st.success("Profile updated.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update profile: {e}")

st.divider()

st.subheader("Change Password")
with st.form("password_form"):
    new_password = st.text_input("New password (min. 6 characters)", type="password")
    confirm_password = st.text_input("Confirm new password", type="password")
    save_password = st.form_submit_button("Update Password", use_container_width=True)

if save_password:
    if not new_password:
        st.error("Please enter a new password.")
    elif new_password != confirm_password:
        st.error("Passwords do not match.")
    elif len(new_password) < 6:
        st.error("Password must be at least 6 characters.")
    else:
        try:
            change_password(sb, new_password)
            st.success("Password updated successfully.")
        except Exception as e:
            st.error(f"Failed to update password: {e}")
