import html
import streamlit as st
from supabase import create_client, Client

ROLE_OPTIONS = ["Academic / Research", "Student", "Industry", "Other"]


@st.cache_resource
def _get_supabase() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


def require_login():
    """
    Call at the top of every page (after set_page_config).
    Handles email verification callbacks, checks session, shows auth page if needed.
    Returns the authenticated Supabase client.
    """
    sb = _get_supabase()
    _handle_email_callback(sb)
    if _is_authenticated(sb):
        return sb
    _hide_sidebar_nav()
    _show_auth_page(sb)
    st.stop()


def _handle_email_callback(sb: Client):
    """
    Handle the redirect from Supabase email verification.
    Supabase appends ?token_hash=xxx&type=email to the Site URL.
    """
    params = st.query_params
    if "token_hash" not in params or "type" not in params:
        return

    try:
        response = sb.auth.verify_otp({
            "token_hash": params["token_hash"],
            "type": params["type"],
        })
        session = response.session
        if session:
            _store_session(session)
            st.query_params.clear()
            st.success("Email verified! You are now signed in.")
            st.rerun()
    except Exception as e:
        st.error(f"Email verification failed: {e}")
        st.query_params.clear()


def _is_authenticated(sb: Client) -> bool:
    if "sb_access_token" not in st.session_state:
        return False
    try:
        sb.auth.set_session(
            st.session_state["sb_access_token"],
            st.session_state["sb_refresh_token"],
        )
        user = sb.auth.get_user()
        if user is None or user.user is None:
            return False
        st.session_state["sb_user_email"] = user.user.email
        st.session_state["sb_user_metadata"] = user.user.user_metadata or {}
        return True
    except Exception:
        st.session_state.pop("sb_access_token", None)
        st.session_state.pop("sb_refresh_token", None)
        st.session_state.pop("sb_user_email", None)
        st.session_state.pop("sb_user_metadata", None)
        return False


def _store_session(session):
    st.session_state["sb_access_token"] = session.access_token
    st.session_state["sb_refresh_token"] = session.refresh_token
    if session.user:
        st.session_state["sb_user_email"] = session.user.email
        st.session_state["sb_user_metadata"] = session.user.user_metadata or {}


def _hide_sidebar_nav():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebar"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _show_auth_page(sb: Client):
    st.markdown(
        """
        <div style="max-width:440px; margin:60px auto 0 auto; text-align:center;">
            <h2 style="color:#1B6B6B; margin-bottom:0.2rem;">A₂A-iCAP Platform</h2>
            <p style="color:#6B7280; font-size:0.97rem; margin-bottom:1.5rem;">
                Sign in or create an account to continue
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

    # ---- Sign In ----
    with tab_signin:
        with st.form("signin_form"):
            email = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter your email and password.")
            else:
                try:
                    response = sb.auth.sign_in_with_password({"email": email, "password": password})
                    _store_session(response.session)
                    st.rerun()
                except Exception as e:
                    err = str(e).lower()
                    if "email not confirmed" in err:
                        st.warning("Please verify your email first. Check your inbox for the confirmation link.")
                    elif "invalid login" in err or "invalid credentials" in err:
                        st.error("Incorrect email or password.")
                    else:
                        st.error(f"Sign in failed: {e}")

    # ---- Sign Up ----
    with tab_signup:
        with st.form("signup_form"):
            new_name = st.text_input("Full name", placeholder="Jane Doe", key="su_name")
            new_email = st.text_input("Email address", placeholder="you@example.com", key="su_email")
            new_affiliation = st.text_input(
                "Affiliation / Organization", placeholder="University or company name", key="su_affiliation"
            )
            new_role = st.selectbox("Role", ROLE_OPTIONS, key="su_role")
            new_pass = st.text_input("Password (min. 6 characters)", type="password", key="su_pass")
            confirm_pass = st.text_input("Confirm password", type="password", key="su_confirm")
            submitted_su = st.form_submit_button("Create Account", use_container_width=True)

        if submitted_su:
            if not new_name or not new_email or not new_affiliation or not new_pass:
                st.error("Please fill in all fields.")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            elif len(new_pass) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                try:
                    sb.auth.sign_up({
                        "email": new_email,
                        "password": new_pass,
                        "options": {
                            "data": {
                                "full_name": new_name.strip(),
                                "affiliation": new_affiliation.strip(),
                                "role": new_role,
                            }
                        },
                    })
                    st.success(
                        f"Account created for **{new_email}**. "
                        "Please check your inbox and click the verification link to activate your account."
                    )
                except Exception as e:
                    err = str(e).lower()
                    if "already registered" in err or "already been registered" in err:
                        st.error("This email is already registered. Please sign in instead.")
                    else:
                        st.error(f"Registration failed: {e}")


def render_sidebar_user(sb: Client):
    """Render signed-in user info and Sign Out button in the sidebar."""
    email = st.session_state.get("sb_user_email", "")
    metadata = st.session_state.get("sb_user_metadata", {}) or {}
    name = metadata.get("full_name", "")
    display_name = html.escape(name) if name else html.escape(email)
    subtitle = f'<br><span style="font-size:0.8rem; color:#6B7280;">{html.escape(email)}</span>' if name else ""
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:10px 0 8px 0; border-bottom:1px solid #D6EFEF; margin-bottom:12px;">
                <span style="font-size:0.85rem; color:#6B7280;">Signed in as</span><br>
                <b style="color:#1B6B6B; font-size:0.93rem;">{display_name}</b>{subtitle}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", use_container_width=True):
            try:
                sb.auth.sign_out()
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()


def update_profile(sb: Client, data: dict) -> None:
    """Update the signed-in user's profile metadata (full_name, affiliation, role)."""
    response = sb.auth.update_user({"data": data})
    if response.user:
        st.session_state["sb_user_metadata"] = response.user.user_metadata or {}


def change_password(sb: Client, new_password: str) -> None:
    """Update the signed-in user's password."""
    sb.auth.update_user({"password": new_password})
