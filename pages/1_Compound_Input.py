import re
import streamlit as st
import pandas as pd
import pubchempy as pcp

from utils.molecule_drawer import render_molecule_2d_bw
from utils.ui_style import apply_poster_style
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


st.set_page_config(page_title="Compound Input", page_icon="🧪", layout="wide")
sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=1)


st.title("🧪 Step 1: Compound Input")


# --------------- Helper functions ---------------

def is_cas_like(text):
    if text is None:
        return False
    return bool(re.fullmatch(r"\d{2,7}-\d{2}-\d", str(text).strip()))


def choose_readable_synonym(synonyms, fallback):
    if not synonyms:
        return fallback
    for synonym in synonyms:
        synonym = str(synonym).strip()
        if not synonym or is_cas_like(synonym):
            continue
        if len(synonym) <= 80:
            return synonym
    return fallback


def lookup_pubchem(identifier):
    try:
        compounds = pcp.get_compounds(identifier, namespace="name")
        if not compounds:
            return None
        compound = compounds[0]
        synonyms = compound.synonyms or []
        matched_name = choose_readable_synonym(synonyms=synonyms, fallback=identifier)
        return {
            "pubchem_cid": compound.cid,
            "matched_name": matched_name,
            "iupac_name": compound.iupac_name,
            "molecular_formula": compound.molecular_formula,
            "molecular_weight": compound.molecular_weight,
            "canonical_smiles": compound.canonical_smiles,
            "isomeric_smiles": compound.isomeric_smiles,
        }
    except Exception as e:
        st.error(f"PubChem lookup failed: {e}")
        return None


# --------------- Action box ---------------

st.markdown(
    """
    <div class="poster-box" style="border-left-color:#1B6B6B; background:#F0FAFA;">
    <b>What to do on this page:</b><br>
    1. Choose how you want to enter your compound (name, CAS No., SMILES, or CSV)<br>
    2. Type the compound or upload a file<br>
    3. Click <b>Resolve compound</b> (or <b>Confirm</b> for CSV) to save it<br>
    4. Then go to <b>Step 2: ML Prediction</b> in the sidebar
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- Input mode ---------------

input_mode = st.selectbox(
    "Input type",
    ["Compound name", "CAS No.", "SMILES", "CSV upload"],
    label_visibility="collapsed",
)

compound_df = None

if input_mode in ["Compound name", "CAS No.", "SMILES"]:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        user_input = st.text_input(
            "Compound identifier",
            placeholder="e.g. caffeine, 58-08-2, or a SMILES string",
        )
    with col_b:
        compound_name = st.text_input(
            "Display name (optional)",
            placeholder="e.g. Caffeine",
        )

    if st.button("🔍 Resolve compound", type="primary"):
        if not user_input.strip():
            st.error("Please enter a compound identifier.")
        else:
            if input_mode == "SMILES":
                display_name = compound_name.strip() if compound_name.strip() else user_input.strip()
                compound_df = pd.DataFrame({
                    "input_type": [input_mode],
                    "input_value": [user_input.strip()],
                    "compound_name": [display_name],
                    "pubchem_cid": [""],
                    "matched_name": [display_name],
                    "iupac_name": [""],
                    "molecular_formula": [""],
                    "molecular_weight": [""],
                    "canonical_smiles": [user_input.strip()],
                    "isomeric_smiles": [""],
                    "status": ["Ready"],
                })
                st.session_state["compound_df"] = compound_df
                st.success("✅ SMILES saved — proceed to Step 2.")
            else:
                with st.spinner("Searching PubChem..."):
                    pubchem_result = lookup_pubchem(user_input.strip())

                if pubchem_result is None:
                    st.error("Compound not found in PubChem. Check the spelling or enter a SMILES directly.")
                else:
                    if compound_name.strip():
                        display_name = compound_name.strip()
                    elif input_mode == "Compound name":
                        display_name = user_input.strip().title()
                    else:
                        display_name = pubchem_result["matched_name"]

                    compound_df = pd.DataFrame({
                        "input_type": [input_mode],
                        "input_value": [user_input.strip()],
                        "compound_name": [display_name],
                        "pubchem_cid": [pubchem_result["pubchem_cid"]],
                        "matched_name": [pubchem_result["matched_name"]],
                        "iupac_name": [pubchem_result["iupac_name"]],
                        "molecular_formula": [pubchem_result["molecular_formula"]],
                        "molecular_weight": [pubchem_result["molecular_weight"]],
                        "canonical_smiles": [pubchem_result["canonical_smiles"]],
                        "isomeric_smiles": [pubchem_result["isomeric_smiles"]],
                        "status": ["Ready"],
                    })
                    st.session_state["compound_df"] = compound_df
                    st.success("✅ Compound found — proceed to Step 2.")

elif input_mode == "CSV upload":
    st.info("CSV must have a compound name column and a SMILES column.")
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None:
        compound_df_raw = pd.read_csv(uploaded_file)

        columns = compound_df_raw.columns.tolist()
        col_a, col_b = st.columns(2)
        with col_a:
            compound_name_col = st.selectbox("Compound name column", columns)
        with col_b:
            smiles_col = st.selectbox("SMILES column", columns)

        with st.expander("Preview uploaded data"):
            st.dataframe(compound_df_raw.head(20), use_container_width=True)

        if st.button("✅ Confirm column mapping", type="primary"):
            compound_df = pd.DataFrame({
                "input_type": ["CSV upload"] * len(compound_df_raw),
                "input_value": compound_df_raw[compound_name_col].astype(str),
                "compound_name": compound_df_raw[compound_name_col].astype(str),
                "canonical_smiles": compound_df_raw[smiles_col].astype(str),
                "status": ["Ready"] * len(compound_df_raw),
            })
            compound_df = compound_df[compound_df["canonical_smiles"].notna()]
            compound_df = compound_df[compound_df["canonical_smiles"].str.strip() != ""]
            compound_df = compound_df.reset_index(drop=True)
            st.session_state["compound_df"] = compound_df
            st.success(f"✅ {len(compound_df)} compounds loaded — proceed to Step 2.")


# --------------- Saved data & preview ---------------

st.divider()

if "compound_df" in st.session_state:
    saved_df = st.session_state["compound_df"]
    st.markdown(f"**Saved compounds: {len(saved_df)}**")

    col_left, col_right = st.columns([1.2, 0.8])

    with col_left:
        st.dataframe(saved_df[["compound_name", "canonical_smiles", "status"]].rename(
            columns={"compound_name": "Name", "canonical_smiles": "SMILES", "status": "Status"}
        ), use_container_width=True)

    with col_right:
        if "compound_name" in saved_df.columns and "canonical_smiles" in saved_df.columns:
            selected_preview = st.selectbox(
                "Preview structure",
                saved_df["compound_name"].astype(str).tolist(),
                key="page1_structure_preview",
            )
            selected_row = saved_df[saved_df["compound_name"].astype(str) == selected_preview].iloc[0]
            selected_smiles = selected_row["canonical_smiles"]
            if pd.isna(selected_smiles) or str(selected_smiles).strip() == "":
                st.warning("No SMILES available.")
            else:
                render_molecule_2d_bw(selected_smiles, caption=selected_preview, width=280, height=220)

    with st.expander("Full compound details"):
        st.dataframe(saved_df, use_container_width=True)

else:
    st.info("No compounds saved yet. Enter a compound above to get started.")

with st.expander("📖 Column reference"):
    st.markdown(
        """
        | Column | Description |
        |--------|-------------|
        | **compound_name** | Display name used throughout the workflow |
        | **canonical_smiles** | Molecular structure used for all calculations |
        | **pubchem_cid** | PubChem ID (empty when SMILES entered directly) |
        | **status** | Ready = compound is ready for the next step |

        **Note:** If the SMILES is invalid, descriptor calculation in Step 2 will fail.
        """
    )
