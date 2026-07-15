import os
import streamlit as st
from utils.ui_style import apply_poster_style, render_dynamic_logo
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


st.set_page_config(
    page_title="A₂A-iCAP Platform",
    page_icon="🧪",
    layout="wide",
)

# --- Authentication gate ---
sb = require_login()

apply_poster_style()

# --- Sidebar ---
render_sidebar_user(sb)
render_wizard_sidebar()

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
    <p style="font-size:1.05rem; color:#374151; margin-top:0.4rem;">
    A computational platform for screening potential A<sub>2A</sub> receptor antagonists
    using AI-based activity prediction, structure-based docking,
    drug-likeness profiling, and consensus ranking.
    </p>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --- Getting Started guide ---
st.markdown("### 🚀 How to use this platform")
st.markdown(
    """
    <div class="poster-box" style="padding:20px 26px;">
    <p style="margin:0 0 14px 0; color:#374151; font-size:0.97rem;">
    Follow these <b>5 steps in order</b>. Each page has a built-in guide
    (📖 Show Guide button in the sidebar) that tells you exactly what to click next.
    </p>
    <table style="width:100%; border-collapse:collapse; font-size:0.95rem;">
      <tr style="background:#EFF9F9;">
        <td style="padding:10px 14px; width:38px; font-size:1.3rem; vertical-align:top;">🧪</td>
        <td style="padding:10px 14px;"><b>Step 1 — Compound Input</b><br>
          <span style="color:#6B7280;">Enter compound names, CAS numbers, SMILES, or upload a CSV.
          The system looks up the structure from PubChem automatically.</span></td>
      </tr>
      <tr>
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">🤖</td>
        <td style="padding:10px 14px;"><b>Step 2 — AI Activity Prediction</b><br>
          <span style="color:#6B7280;">Click <b>Run ML prediction</b> to predict A<sub>2A</sub> receptor antagonist activity.
          Results include a probability score and Applicability Domain (AD) assessment.</span></td>
      </tr>
      <tr style="background:#EFF9F9;">
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">🧬</td>
        <td style="padding:10px 14px;"><b>Step 3 — Docking Evidence</b><br>
          <span style="color:#6B7280;">Run structure-based docking or upload a pre-computed docking result CSV.
          Binding affinity ≤ −7.5 kcal/mol = Strong evidence.</span></td>
      </tr>
      <tr>
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">📊</td>
        <td style="padding:10px 14px;"><b>Step 4 — Drug-Likeness Assessment</b><br>
          <span style="color:#6B7280;">Physicochemical properties are calculated automatically from SMILES
          and displayed on a Radar Plot compared to an ideal drug profile. No button press needed.</span></td>
      </tr>
      <tr style="background:#EFF9F9;">
        <td style="padding:10px 14px; font-size:1.3rem; vertical-align:top;">🏆</td>
        <td style="padding:10px 14px;"><b>Step 5 — Consensus Ranking</b><br>
          <span style="color:#6B7280;">Click <b>Generate Consensus Ranking</b> to combine all evidence streams.
          Compounds are ranked as <b>Tier 1</b> (high priority), <b>Tier 2</b> (moderate), or <b>Tier 3</b> (low).</span></td>
      </tr>
    </table>
    <p style="margin:14px 0 0 0; color:#6B7280; font-size:0.88rem;">
    💡 <b>Tip:</b> Use the <b>sidebar navigation</b> to jump between steps at any time.
    Click 📖 Show Guide in the sidebar to open step-specific instructions on any page.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --- Scoring summary ---
st.subheader("Consensus Scoring Criteria")

st.markdown(
    """
    <div class="poster-box consensus-box">
    <b>Rule-based Consensus Scoring</b><br><br>
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
    <span class="tier1-badge">Tier 1</span> Score ≥ 6 — High-priority compound &nbsp;
    <span class="tier2-badge">Tier 2</span> Score 3–5 — Moderate priority &nbsp;
    <span class="tier3-badge">Tier 3</span> Score &lt; 3 — Low priority
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --- Disclaimer ---
st.subheader("Disclaimer")
st.markdown(
    """
    <div class="poster-box">
    This platform is intended for early-stage computational screening in research.
    All results (AI prediction, docking affinity, drug-likeness, consensus tier)
    are computational estimates only. <b>They do not constitute experimental confirmation.</b>
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
