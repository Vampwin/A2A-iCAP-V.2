import streamlit as st

STEPS = {
    1: {
        "title": "Step 1 — Compound Input",
        "icon": "🧪",
        "page": "Compound Input",
        "what_to_do": [
            "Choose an input type (name, CAS No., SMILES, or CSV)",
            "Type the compound identifier or upload a file",
            'Click **Resolve compound** (or **Confirm** for CSV)',
            "Go to **Step 2: ML Prediction** in the sidebar",
        ],
        "tip": "Entering a name like `caffeine` triggers automatic PubChem lookup.",
    },
    2: {
        "title": "Step 2 — AI Activity Prediction",
        "icon": "🤖",
        "page": "ML Prediction",
        "what_to_do": [
            "Adjust the threshold slider if needed (default 0.50 is fine)",
            "Click **▶ Run ML prediction**",
            "Check each compound's Active Probability and AD status",
            "Go to **Step 3: Docking Evidence** in the sidebar",
        ],
        "tip": "Higher threshold = more stringent = fewer false positives.",
    },
    3: {
        "title": "Step 3 — Docking Evidence",
        "icon": "🧬",
        "page": "Docking Evidence",
        "what_to_do": [
            "Select a compound from the dropdown",
            "Choose **Upload precomputed docking result** (most users)",
            "Upload a CSV with compound name and docking affinity (kcal/mol) columns",
            'Click **✅ Confirm docking result**',
            "Go to **Step 4: Drug-Likeness** in the sidebar",
        ],
        "tip": "Docking affinity ≤ −7.5 kcal/mol = Strong · ≤ −6.5 = Moderate · > −6.5 = Weak",
    },
    4: {
        "title": "Step 4 — Drug-Likeness",
        "icon": "📊",
        "page": "Drug-Likeness",
        "what_to_do": [
            "Results are calculated automatically — no button press needed",
            "Select a compound to view its Radar Plot",
            "Check the Drug-Likeness level (Favorable / Borderline / Concern)",
            "Go to **Step 5: Consensus Ranking** in the sidebar",
        ],
        "tip": "Closer to 1.0 on each radar axis = better drug-like property.",
    },
    5: {
        "title": "Step 5 — Consensus Ranking",
        "icon": "🏆",
        "page": "Consensus Ranking",
        "what_to_do": [
            "Click **▶ Generate Consensus Ranking**",
            "The platform combines AI + docking + drug-likeness scores",
            "Compounds are ranked Tier 1 (high) · Tier 2 (moderate) · Tier 3 (low)",
            "Download the results CSV",
        ],
        "tip": "Steps 1–4 must all be completed before ranking can be generated.",
    },
}


def init_wizard():
    if "wizard_open" not in st.session_state:
        st.session_state["wizard_open"] = False


def render_wizard_sidebar(current_step: int = None):
    """Render the guide toggle + guide content entirely in the sidebar."""
    init_wizard()

    with st.sidebar:
        st.markdown("---")
        is_open = st.session_state.get("wizard_open", False)
        btn_label = "📖 Hide Step Guide" if is_open else "📖 Show Step Guide"
        if st.button(btn_label, use_container_width=True):
            st.session_state["wizard_open"] = not is_open
            st.rerun()

        if st.session_state.get("wizard_open") and current_step and current_step in STEPS:
            step = STEPS[current_step]
            total = len(STEPS)

            st.markdown(
                f"""
                <div style="
                    background:#EFF9F9; border:1.5px solid #1B6B6B;
                    border-radius:12px; padding:14px 16px; margin-top:8px;
                ">
                <div style="font-weight:700; color:#1B6B6B; font-size:0.95rem; margin-bottom:8px;">
                    {step['icon']} {step['title']}
                    <span style="float:right; color:#9CA3AF; font-size:0.78rem;">{current_step}/{total}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.progress(current_step / total)

            steps_html = ""
            for i, action in enumerate(step["what_to_do"], 1):
                steps_html += f'<div style="margin:4px 0; font-size:0.88rem; color:#1F2937;"><b>{i}.</b> {action}</div>'

            st.markdown(
                f"""
                {steps_html}
                <div style="margin-top:10px; background:#FFFBEB; border-left:3px solid #F59E0B;
                    padding:6px 10px; border-radius:6px; font-size:0.84rem; color:#4B5563;">
                    💡 {step['tip']}
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
