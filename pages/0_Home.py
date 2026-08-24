import os

import streamlit as st

from utils.auth import get_auth_state, render_sidebar_user
from utils.ui_style import apply_poster_style, render_dynamic_logo, render_glossary_sidebar
from utils.wizard import render_wizard_sidebar


# Home is intentionally public. Screening and account pages remain protected.
sb, signed_in = get_auth_state()
apply_poster_style()

if signed_in and sb is not None:
    render_sidebar_user(sb)
    render_wizard_sidebar()
else:
    with st.sidebar:
        st.markdown(
            """
            <div style="background:#EFF9F9;border:1px solid #BFE3E3;border-radius:12px;
                        padding:12px 14px;margin:0.25rem 0 0.75rem 0;">
                <b style="color:#145555;">Public overview</b><br>
                <span style="font-size:0.84rem;color:#4B5563;">
                    Sign in when you are ready to screen candidates.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

render_glossary_sidebar()


# --- Public, decision-first hero ---
hero_copy, hero_visual = st.columns([1.08, 0.92], gap="large")
with hero_copy:
    st.markdown(
        """
        <div class="public-hero">
            <div class="hero-kicker">AI-integrated candidate prioritization</div>
            <h1 class="hero-title">Choose the right molecules to test next.</h1>
            <p class="hero-copy">
                A₂A-iCAP turns a long candidate list into a clear, explainable shortlist.
                It compares AI-predicted activity, simulated receptor fit, and early
                developability so research teams can focus laboratory time and budget.
            </p>
            <div class="trust-row">
                <span class="trust-chip">✓ Three evidence streams</span>
                <span class="trust-chip">✓ Explainable recommendations</span>
                <span class="trust-chip">✓ Research-first workflow</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        "🚀 Open screening workspace" if signed_in else "🚀 Sign in to start screening",
        type="primary",
        key="hero_screening_cta",
    ):
        st.switch_page("pages/1_Compound_Input.py")

with hero_visual:
    logo_video_path = "assets/I_want_some_dynamic_logo_on_my.mp4"
    logo_path = "assets/a2a_icap_logo.png"
    if not render_dynamic_logo(logo_video_path, max_width="520px"):
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown(
                "<div class='sample-result'><h4>A₂A-iCAP Platform</h4>"
                "<span>AI-Integrated Candidate Assessment and Prioritization</span></div>",
                unsafe_allow_html=True,
            )

st.divider()


# --- Investor-facing value summary ---
st.markdown("### Three questions answered in one workflow")
value_col1, value_col2, value_col3 = st.columns(3)
with value_col1:
    st.markdown(
        """
        <div class="decision-card">
            <div class="decision-icon">🎯</div>
            <b>Is there an early activity signal?</b><br>
            <span>AI estimates whether each molecule may affect the A₂A receptor and reports the probability.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with value_col2:
    st.markdown(
        """
        <div class="decision-card">
            <div class="decision-icon">🧩</div>
            <b>Do independent signals agree?</b><br>
            <span>Activity, simulated fit, and molecular properties are reviewed side by side—not as a black box.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with value_col3:
    st.markdown(
        """
        <div class="decision-card">
            <div class="decision-icon">🧪</div>
            <b>What is the next scientific action?</b><br>
            <span>Each candidate receives a plain-language outcome: advance, review, or defer.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.info(
    "**Decision scope:** A₂A-iCAP prioritizes early experiments. It does not predict clinical success, "
    "safety, market size, development cost, or investment return."
)

st.divider()


# --- Show what the user will receive before asking them to sign in ---
st.markdown("### See the decision—not just another score")
st.markdown(
    """
    <div class="sample-result">
        <div style="color:#6B7280;font-size:0.78rem;font-weight:800;letter-spacing:0.07em;
                    text-transform:uppercase;margin-bottom:5px;">Illustrative candidate result</div>
        <h4>Advance to laboratory validation</h4>
        <p style="color:#374151;margin:0 0 14px 0;">
            The three early screens provide a consistent case for scientific follow-up.
            The result explains both the recommendation and the evidence behind it.
        </p>
        <div class="trust-row">
            <span class="trust-chip">AI-estimated Active: 82%</span>
            <span class="trust-chip">Simulated fit: Strong</span>
            <span class="trust-chip">Early developability: Favorable</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# --- Responsive workflow overview ---
st.markdown("### From candidate list to laboratory shortlist")
st.markdown(
    """
    <p class="small-note">Five guided steps keep the scientific logic visible while technical details remain available for review.</p>
    <div class="workflow-grid">
        <div class="workflow-card">
            <div class="workflow-number">1</div><br>
            <b>Add candidates</b><br>
            <span>Enter or upload molecules and confirm each chemical structure.</span>
        </div>
        <div class="workflow-card">
            <div class="workflow-number">2</div><br>
            <b>Screen activity</b><br>
            <span>Estimate the chance of an early A₂A receptor activity signal.</span>
        </div>
        <div class="workflow-card">
            <div class="workflow-number">3</div><br>
            <b>Check simulated fit</b><br>
            <span>Add an independent estimate of how well each candidate may fit the receptor.</span>
        </div>
        <div class="workflow-card">
            <div class="workflow-number">4</div><br>
            <b>Review developability</b><br>
            <span>Identify basic molecular-property concerns early in the process.</span>
        </div>
        <div class="workflow-card">
            <div class="workflow-number">5</div><br>
            <b>Build the shortlist</b><br>
            <span>Combine the evidence into a transparent outcome and next action.</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Technical details: How the shortlist score is calculated"):
    st.markdown(
        """
        The platform uses a transparent evidence score (maximum 8 points):

        | Evidence condition | Points |
        |---|---:|
        | AI activity signal is Promising | +2 |
        | AI activity signal is Possible | +1 |
        | Active probability ≥ 0.80 | +1 |
        | Inside the model applicability domain | +1 |
        | Simulated fit is Strong / Moderate | +2 / +1 |
        | Early developability is Favorable / Borderline | +2 / +1 |

        The score supports prioritization; it is **not** a probability of technical, clinical, or commercial success.
        """
    )

st.divider()


# --- Responsible use and credibility ---
st.markdown("### Built for responsible early-stage decisions")
responsible_col, trust_col = st.columns([1.05, 0.95])
with responsible_col:
    st.markdown(
        """
        <div class="poster-box">
            Use the ranking to decide which compounds deserve closer scientific review and laboratory testing.
            Every result is a computational estimate. <b>A high-ranked candidate is a better-supported
            hypothesis—not a proven drug, validated asset, or guarantee of commercial success.</b>
        </div>
        """,
        unsafe_allow_html=True,
    )
with trust_col:
    st.markdown(
        """
        <div class="poster-box consensus-box">
            <b>Academic affiliation</b><br><br>
            Faculty of Pharmaceutical Sciences, Chulalongkorn University<br>
            Center of Excellence in Natural Products for Ageing and Chronic Diseases
            <br><br><b>Supported by AI Longevity Co., Ltd.</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

if not signed_in:
    st.markdown(
        """
        <div class="sample-result" style="text-align:center;margin-top:1.25rem;">
            <h4>Ready to compare your candidates?</h4>
            <p style="color:#4B5563;margin:0;">Create a research account or sign in to open the screening workspace.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🚀 Sign in to start screening", type="primary", key="footer_screening_cta"):
        st.switch_page("pages/1_Compound_Input.py")
