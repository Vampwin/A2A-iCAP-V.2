"""Application entrypoint and navigation router."""

import streamlit as st


st.set_page_config(page_title="A₂A-iCAP Platform", page_icon="🧪", layout="wide")

pages = [
    st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True),
    st.Page(
        "pages/1_Compound_Input.py",
        title="Add Candidates",
        icon="🧪",
        url_path="Compound_Input",
    ),
    st.Page(
        "pages/2_ML_Prediction.py",
        title="AI Target Screen",
        icon="🤖",
        url_path="ML_Prediction",
    ),
    st.Page(
        "pages/3_Docking_Evidence.py",
        title="Simulated Target Fit",
        icon="🧬",
        url_path="Docking_Evidence",
    ),
    st.Page(
        "pages/4_Drug_Likeness.py",
        title="Early Developability",
        icon="📊",
        url_path="Drug_Likeness",
    ),
    st.Page(
        "pages/5_Consensus_Ranking.py",
        title="Candidate Shortlist",
        icon="🏆",
        url_path="Consensus_Ranking",
    ),
    st.Page(
        "pages/6_Account_Settings.py",
        title="Account Settings",
        icon="👤",
        url_path="Account_Settings",
    ),
]

navigation = st.navigation(pages, position="sidebar")
navigation.run()
