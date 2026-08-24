import streamlit as st

STEPS = {
    1: {
        "title": "Step 1 — Add candidates",
        "icon": "🧪",
        "page": "Add Candidates",
        "what_to_do": [
            "Choose how you want to add candidates",
            "Enter a name or identifier, or upload a candidate list",
            'Click **Resolve compound** (or **Confirm** for CSV)',
            "Go to **Step 2: AI Target Screen** in the sidebar",
        ],
        "tip": "The chemical structure is the common reference used throughout all five steps.",
    },
    2: {
        "title": "Step 2 — Screen target activity",
        "icon": "🤖",
        "page": "AI Target Screen",
        "what_to_do": [
            "Keep the default activity cutoff unless a scientist advises otherwise",
            "Click **▶ Run ML prediction**",
            "Review the AI signal and its confidence level",
            "Go to **Step 3: Simulated Target Fit** in the sidebar",
        ],
        "tip": "Treat this as an early signal. A positive result still needs independent evidence.",
    },
    3: {
        "title": "Step 3 — Check simulated fit",
        "icon": "🧬",
        "page": "Simulated Target Fit",
        "what_to_do": [
            "Select a compound from the dropdown",
            "Choose **Upload precomputed docking result** (most users)",
            "Upload a CSV with candidate name and simulated-fit score columns",
            'Click **✅ Confirm docking result**',
            "Go to **Step 4: Early Developability** in the sidebar",
        ],
        "tip": "A more negative score suggests a tighter simulated fit; it does not confirm laboratory binding.",
    },
    4: {
        "title": "Step 4 — Check developability",
        "icon": "📊",
        "page": "Early Developability",
        "what_to_do": [
            "Results are calculated automatically — no button press needed",
            "Select a candidate to view its property profile",
            "Check whether any basic molecular properties raise an early concern",
            "Go to **Step 5: Candidate Shortlist** in the sidebar",
        ],
        "tip": "This screen does not assess safety, efficacy, formulation, or clinical success.",
    },
    5: {
        "title": "Step 5 — Build the shortlist",
        "icon": "🏆",
        "page": "Candidate Shortlist",
        "what_to_do": [
            "Click **▶ Build candidate shortlist**",
            "The platform combines the three screening signals",
            "Tier 1 candidates are supported for earlier laboratory review",
            "Download the results CSV",
        ],
        "tip": "The ranking explains where to investigate next; it is not an investment recommendation.",
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
