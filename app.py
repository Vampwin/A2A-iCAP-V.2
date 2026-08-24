"""Application entrypoint and navigation router."""

import streamlit as st


st.set_page_config(page_title="A₂A-iCAP Platform", page_icon="🧪", layout="wide")

pages = {
    "Overview": [
        st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True),
    ],
    "Screening workflow": [
        st.Page(
            "pages/1_Compound_Input.py",
            title="1. Add Candidates",
            icon="🧪",
            url_path="Compound_Input",
        ),
        st.Page(
            "pages/2_ML_Prediction.py",
            title="2. AI Target Screen",
            icon="🤖",
            url_path="ML_Prediction",
        ),
        st.Page(
            "pages/3_Docking_Evidence.py",
            title="3. Simulated Target Fit",
            icon="🧬",
            url_path="Docking_Evidence",
        ),
        st.Page(
            "pages/4_Drug_Likeness.py",
            title="4. Early Developability",
            icon="📊",
            url_path="Drug_Likeness",
        ),
        st.Page(
            "pages/5_Consensus_Ranking.py",
            title="5. Candidate Shortlist",
            icon="🏆",
            url_path="Consensus_Ranking",
        ),
    ],
    "Account": [
        st.Page(
            "pages/6_Account_Settings.py",
            title="Account Settings",
            icon="👤",
            url_path="Account_Settings",
        ),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
