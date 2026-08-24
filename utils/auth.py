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


def get_auth_state():
    """Return ``(client, signed_in)`` without gating a public page.

    Anonymous visitors should be able to read the public Home page without
    opening a Supabase connection. A client is created only when a saved
    session or an email-verification callback needs to be handled.
    """
    has_saved_session = "sb_access_token" in st.session_state
    has_email_callback = "token_hash" in st.query_params and "type" in st.query_params
    if not has_saved_session and not has_email_callback:
        return None, False

    try:
        sb = _get_supabase()
        _handle_email_callback(sb)
        return sb, _is_authenticated(sb)
    except Exception:
        return None, False


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
        .block-container { max-width: 1040px !important; padding-top: 1.25rem !important; }
        div[data-testid="stTabs"] { max-width: 500px; margin: 0 auto; }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 0.35rem; }
        div[data-testid="stTabs"] [data-baseweb="tab"] {
            flex: 1; justify-content: center; min-height: 46px;
        }
        div[data-testid="stPageLink"] { width: fit-content; }
        div[data-testid="stPageLink"] a {
            color:#145555 !important; font-weight:700; text-decoration:none;
            border:1px solid #BFE3E3; border-radius:10px; padding:0.5rem 0.75rem;
            background:#EFF9F9;
        }
        div[data-testid="stFormSubmitButton"] button {
            background:#1B6B6B; color:#FFFFFF; border:1px solid #1B6B6B;
            border-radius:10px; min-height:44px; font-weight:700;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background:#145555; color:#FFFFFF; border-color:#145555;
        }
        @media (max-width: 640px) {
            .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _show_auth_page(sb: Client):
    st.page_link("pages/0_Home.py", label="Back to public overview", icon="🏠")
    st.markdown(
        """
        <div style="max-width:620px; margin:1.1rem auto 1.25rem auto; text-align:center;">
            <div style="display:inline-flex; align-items:center; gap:8px; color:#1B6B6B;
                        font-size:0.82rem; font-weight:800; letter-spacing:0.08em;
                        text-transform:uppercase; margin-bottom:0.55rem;">
                Secure research workspace
            </div>
            <h1 style="color:#164E63; font-size:clamp(2rem, 5vw, 3.2rem); line-height:1.08;
                       margin:0 0 0.7rem 0;">A₂A-iCAP Platform</h1>
            <p style="color:#4B5563; font-size:1.03rem; line-height:1.6; margin:0 auto; max-width:560px;">
                Sign in to screen candidate molecules, compare three early evidence streams,
                and build an explainable shortlist for laboratory follow-up.
            </p>
            <div style="display:flex; justify-content:center; flex-wrap:wrap; gap:8px; margin-top:1rem;">
                <span style="background:#EFF9F9; color:#145555; border:1px solid #BFE3E3;
                             border-radius:999px; padding:5px 11px; font-size:0.82rem;">AI activity</span>
                <span style="background:#EFF9F9; color:#145555; border:1px solid #BFE3E3;
                             border-radius:999px; padding:5px 11px; font-size:0.82rem;">Simulated fit</span>
                <span style="background:#EFF9F9; color:#145555; border:1px solid #BFE3E3;
                             border-radius:999px; padding:5px 11px; font-size:0.82rem;">Developability</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

    # ---- Sign In ----
    with tab_signin:
        st.caption("Access your saved screening workspace.")
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
        st.caption("Create a research account to begin screening candidates.")
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
