import os
import streamlit as st
from utils.ui_style import apply_poster_style, render_dynamic_logo, render_glossary_sidebar
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


# --- Authentication gate ---
sb = require_login()

apply_poster_style()

# --- Sidebar ---
render_sidebar_user(sb)
render_wizard_sidebar()
render_glossary_sidebar()

# --- Header ---
logo_video_path = "assets/I_want_some_dynamic_logo_on_my.mp4"
logo_path = "assets/a2a_icap_logo.png"
if not render_dynamic_logo(logo_video_path, max_width="620px"):
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown(
            "<h1 style='color:#1B6B6B;'>A₂A-iCAP Platform</h1>",
            unsafe_allow_html=True,
        )

st.markdown(
    """
    <p style="font-size:1.12rem; color:#374151; margin-top:0.4rem; line-height:1.65;">
    Turn a long list of molecules into a clear shortlist for laboratory testing.
    A<sub>2A</sub>-iCAP compares three early signals—AI-predicted activity,
    simulated receptor fit, and basic drug-like properties—so teams can focus
    time and budget on the most promising candidates.
    </p>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --- Investor-facing value summary ---
st.markdown("### What this platform helps you decide")
value_col1, value_col2, value_col3 = st.columns(3)
with value_col1:
    st.markdown(
        """
        <div class="decision-card">
        <div class="decision-icon">🎯</div>
        <b>Is there an early target signal?</b><br>
        <span>AI estimates whether each molecule may block the A<sub>2A</sub> receptor.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with value_col2:
    st.markdown(
        """
        <div class="decision-card">
        <div class="decision-icon">🧩</div>
        <b>Do the signals agree?</b><br>
        <span>The platform compares AI, binding simulation, and developability indicators.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with value_col3:
    st.markdown(
        """
        <div class="decision-card">
        <div class="decision-icon">🧪</div>
        <b>What should be tested next?</b><br>
        <span>Candidates are ranked to support a focused, explainable laboratory plan.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.info(
    "**Decision scope:** This is an early research-screening tool. It helps prioritize experiments; "
    "it does not predict clinical success, safety, market size, development cost, or investment return."
)

st.divider()

# --- Getting Started guide ---
st.markdown("### 🚀 How the screening funnel works")
st.markdown(
    """
    <div class="poster-box" style="padding:20px 26px;">
    <p style="margin:0 0 14px 0; color:#374151; font-size:0.97rem;">
    Follow five steps to move from a broad candidate list to a documented shortlist.
    No scientific background is needed to read the headline result; technical details remain available for review.
    </p>
    <table style="width:100%; border-collapse:collapse; font-size:0.95rem;">
      <tr style="background:#EFF9F9;">
        <td style="padding:10px 14px; width:38px; font-size:1.3rem; vertical-align:top;">🧪</td>
        <td style="padding:10px 14px;"><b>Step 1 — Add candidates</b><br>
          <span style="color:#6B7280;">Enter the molecules you want to compare. The platform retrieves or validates each chemical structure.</span></td>
      </tr>
      <tr>
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">🤖</td>
        <td style="padding:10px 14px;"><b>Step 2 — Screen for target activity</b><br>
          <span style="color:#6B7280;">AI looks for an early signal that a molecule may block the A<sub>2A</sub> receptor and shows how much confidence to place in that estimate.</span></td>
      </tr>
      <tr style="background:#EFF9F9;">
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">🧬</td>
        <td style="padding:10px 14px;"><b>Step 3 — Check simulated target fit</b><br>
          <span style="color:#6B7280;">A molecular simulation estimates how well each candidate may fit the receptor. This adds a second, independent screening signal.</span></td>
      </tr>
      <tr>
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">📊</td>
        <td style="padding:10px 14px;"><b>Step 4 — Check early developability</b><br>
          <span style="color:#6B7280;">Basic molecular properties flag candidates that may be harder to develop. This is an early filter, not a safety or clinical assessment.</span></td>
      </tr>
      <tr style="background:#EFF9F9;">
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">🏆</td>
        <td style="padding:10px 14px;"><b>Step 5 — Build the shortlist</b><br>
          <span style="color:#6B7280;">The three evidence streams are combined into a transparent priority ranking, with a clear reason for each candidate's position.</span></td>
      </tr>
    </table>
    <p style="margin:14px 0 0 0; color:#6B7280; font-size:0.88rem;">
    💡 <b>Tip:</b> Use the sidebar to move between steps. Open <b>Show Step Guide</b> whenever you want a short explanation of the current screen.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --- Scoring summary ---
with st.expander("Technical details: How the shortlist score is calculated"):
    st.markdown(
        """
    <div class="poster-box consensus-box" style="margin-bottom:0;">
    <b>Transparent evidence scoring (maximum 8 points)</b><br><br>
    <table style="width:100%; font-size:0.97rem; border-collapse:collapse;">
      <tr><td style="padding:3px 8px;">✅ AI predicts Active</td><td style="padding:3px 8px; font-weight:700; color:#065F46;">+2 points</td></tr>
      <tr><td style="padding:3px 8px;">✅ Active probability ≥ 0.80</td><td style="padding:3px 8px; font-weight:700; color:#065F46;">+1 point</td></tr>
      <tr><td style="padding:3px 8px;">✅ Inside Applicability Domain</td><td style="padding:3px 8px; font-weight:700; color:#065F46;">+1 point</td></tr>
      <tr><td style="padding:3px 8px;">✅ Docking Strong (≤ -7.5 kcal/mol)</td><td style="padding:3px 8px; font-weight:700; color:#065F46;">+2 points</td></tr>
      <tr><td style="padding:3px 8px;">✅ Docking Moderate (≤ -6.5 kcal/mol)</td><td style="padding:3px 8px; font-weight:700; color:#065F46;">+1 point</td></tr>
      <tr><td style="padding:3px 8px;">✅ Drug-likeness Favorable</td><td style="padding:3px 8px; font-weight:700; color:#065F46;">+2 points</td></tr>
      <tr><td style="padding:3px 8px;">✅ Drug-likeness Borderline</td><td style="padding:3px 8px; font-weight:700; color:#065F46;">+1 point</td></tr>
    </table>
    <br>
    <span class="tier1-badge">Advance to lab validation</span> Score ≥ 6 (technical: Tier 1)<br><br>
    <span class="tier2-badge">Review or optimize</span> Score 3–5 (technical: Tier 2)<br><br>
    <span class="tier3-badge">Defer or redesign</span> Score &lt; 3 (technical: Tier 3)
    </div>
    """,
        unsafe_allow_html=True,
    )

st.divider()

# --- Disclaimer ---
st.subheader("How to use the result responsibly")
st.markdown(
    """
    <div class="poster-box">
    Use the ranking to decide which compounds deserve closer scientific review and laboratory testing.
    Every result is a computational estimate. <b>A high-ranked candidate is a better-supported hypothesis,
    not a proven drug, validated asset, or guarantee of commercial success.</b>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --- Affiliations & Acknowledgement ---
st.subheader("Affiliations & Acknowledgement")

aff_col, ack_col = st.columns([1.2, 0.8])

with aff_col:
    st.markdown(
        """
        <div class="poster-box" style="height:100%;">
        <b>Affiliations</b><br><br>
        Faculty of Pharmaceutical Sciences, Chulalongkorn University<br>
        Center of Excellence in Natural Products for Ageing and Chronic Diseases,
        Chulalongkorn University
        </div>
        """,
        unsafe_allow_html=True,
    )

with ack_col:
    company_logo_path = "assets/ai_longevity_logo.jpg"
    inner_col1, inner_col2 = st.columns([0.35, 0.65])
    with inner_col1:
        if os.path.exists(company_logo_path):
            st.image(company_logo_path, use_container_width=True)
        else:
            st.markdown(
                '<div class="poster-box consensus-box" style="text-align:center;"><b>AI Longevity<br>Co., Ltd.</b></div>',
                unsafe_allow_html=True,
            )
    with inner_col2:
        st.markdown(
            """
            <div class="poster-box consensus-box" style="height:100%;">
            We gratefully acknowledge<br><b>AI Longevity Co., Ltd.</b><br>for their support.
            </div>
            """,
            unsafe_allow_html=True,
        )
