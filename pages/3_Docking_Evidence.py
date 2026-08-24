import os
import pandas as pd
import numpy as np
import streamlit as st

from utils.ui_style import apply_poster_style, status_badge, render_badge_row, render_glossary_sidebar
from utils.molecule_drawer import render_molecule_2d
from utils.vina_runner import run_vina_docking_for_compound
from utils.pose_viewer import render_docking_pose_3d
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=3)
render_glossary_sidebar()


st.title("🧬 Step 3: Check simulated target fit")
st.caption("A molecular simulation provides a second screening signal that is independent of the AI model.")

# --------------- Guard ---------------

if "compound_df" not in st.session_state:
    st.warning("⬅️ No compounds loaded — please complete **Step 1: Compound Input** first.")
    st.stop()

compound_df = st.session_state["compound_df"].copy()
if "compound_name" not in compound_df.columns:
    compound_df["compound_name"] = compound_df["input_value"].astype(str)

# --------------- Action box ---------------

st.markdown(
    """
    <div class="poster-box" style="border-left-color:#2E5FA3; background:#F0F4FF;">
    <b>Decision question:</b> Does the candidate also show a convincing simulated fit with the A<sub>2A</sub> receptor?<br><br>
    Add existing simulation results or run the advanced local workflow. A strong result supports
    prioritization, but still requires laboratory confirmation.
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- Compound selection ---------------

compound_list = compound_df["compound_name"].astype(str).tolist()
selected_compound = st.selectbox("Select candidate", compound_list)
selected_row = compound_df[compound_df["compound_name"].astype(str) == selected_compound].iloc[0]
selected_smiles = selected_row["canonical_smiles"]

with st.expander("View candidate structure and technical details"):
    col_structure, col_info = st.columns([0.8, 1.6])
    with col_structure:
        if pd.isna(selected_smiles) or str(selected_smiles).strip() == "":
            st.warning("No SMILES available.")
        else:
            render_molecule_2d(selected_smiles, caption=selected_compound, width=340, height=260)
    with col_info:
        disp_cols = ["compound_name", "canonical_smiles", "pubchem_cid", "molecular_formula", "molecular_weight"]
        disp_cols = [c for c in disp_cols if c in selected_row.index]
        st.dataframe(pd.DataFrame([selected_row[disp_cols]]), use_container_width=True)
        st.dataframe(compound_df[["compound_name", "canonical_smiles", "status"]], use_container_width=True)

st.divider()

# --------------- Docking mode ---------------

dock_mode = st.radio(
    "How will you add the simulation result?",
    ["Upload precomputed docking result", "Run local docking (advanced)"],
    index=0,
    format_func=lambda option: {
        "Upload precomputed docking result": "Upload existing simulation results (recommended)",
        "Run local docking (advanced)": "Run a new simulation on this machine (advanced)",
    }[option],
)

# --------------- Mode 1: Upload precomputed ---------------

if dock_mode == "Upload precomputed docking result":
    st.info("Upload a CSV or Excel file containing a candidate name and simulated affinity score (kcal/mol).")

    uploaded_docking = st.file_uploader("Upload docking result", type=["csv", "xlsx"])

    if uploaded_docking is not None:
        docking_raw = (
            pd.read_csv(uploaded_docking)
            if uploaded_docking.name.lower().endswith(".csv")
            else pd.read_excel(uploaded_docking)
        )

        with st.expander("Preview uploaded data"):
            st.dataframe(docking_raw.head(20), use_container_width=True)

        columns = docking_raw.columns.tolist()
        col_a, col_b = st.columns(2)
        with col_a:
            compound_col = st.selectbox("Compound name column", columns, key="dock_compound_col")
        with col_b:
            affinity_col = st.selectbox("Docking affinity column (kcal/mol)", columns, key="dock_affinity_col")

        if st.button("✅ Confirm docking result", type="primary"):
            docking_df = pd.DataFrame({
                "compound_name": docking_raw[compound_col].astype(str),
                "vina_affinity_kcal_mol": pd.to_numeric(docking_raw[affinity_col], errors="coerce"),
            })
            docking_df = docking_df.dropna(subset=["compound_name", "vina_affinity_kcal_mol"]).reset_index(drop=True)
            input_compounds = compound_df["compound_name"].astype(str).tolist()
            docking_df = docking_df[docking_df["compound_name"].isin(input_compounds)].reset_index(drop=True)
            docking_df["docking_evidence"] = np.where(
                docking_df["vina_affinity_kcal_mol"] <= -7.5, "Strong",
                np.where(docking_df["vina_affinity_kcal_mol"] <= -6.5, "Moderate", "Weak"),
            )
            docking_df["docking_engine"] = "Molecular Docking"
            docking_df["docking_note"] = "Precomputed result imported"
            docking_df["output_pose_pdbqt"] = ""
            docking_df["vina_log"] = ""
            st.session_state["docking_df"] = docking_df
            st.success("✅ Docking result saved — proceed to Step 4.")

# --------------- Mode 2: Run local docking ---------------

elif dock_mode == "Run local docking (advanced)":
    receptor_path = "data/receptor.pdbqt"
    config_path = "data/vina_config.json"
    receptor_exists = os.path.exists(receptor_path)
    config_exists = os.path.exists(config_path)

    st.info("Docking software must be configured on this machine. Contact your system administrator if unsure.")
    run_scope = st.radio("Docking scope", ["Selected compound only", "All compounds"], index=0)

    if not receptor_exists or not config_exists:
        st.error("Receptor or configuration file missing — local docking is unavailable.")
    else:
        if st.button("▶ Run Docking", type="primary"):
            docking_input_df = (
                pd.DataFrame([selected_row]) if run_scope == "Selected compound only" else compound_df.copy()
            )
            docking_results = []
            progress = st.progress(0)
            status_box = st.empty()
            total = len(docking_input_df)

            for i, (_, row) in enumerate(docking_input_df.iterrows(), start=1):
                cname = str(row["compound_name"])
                smi = str(row["canonical_smiles"])
                status_box.info(f"Processing: {cname} ({i}/{total})")
                try:
                    result = run_vina_docking_for_compound(compound_name=cname, smiles=smi)
                    result["docking_engine"] = "Molecular Docking"
                    docking_results.append(result)
                except Exception as e:
                    docking_results.append({
                        "compound_name": cname,
                        "vina_affinity_kcal_mol": np.nan,
                        "docking_evidence": "Failed",
                        "docking_engine": "Molecular Docking",
                        "output_pose_pdbqt": "",
                        "vina_log": "",
                        "docking_note": f"Docking failed: {e}",
                    })
                progress.progress(i / total)

            docking_df = pd.DataFrame(docking_results)
            st.session_state["docking_df"] = docking_df
            status_box.success("✅ Docking complete — proceed to Step 4.")

# --------------- Results ---------------

st.divider()

if "docking_df" in st.session_state:
    docking_df = st.session_state["docking_df"].copy()

    display_df = docking_df[["compound_name", "vina_affinity_kcal_mol", "docking_evidence"]].copy()
    display_df.columns = ["Candidate", "Simulated score (kcal/mol)", "Fit signal"]
    st.dataframe(display_df, use_container_width=True)

    sel_df = docking_df[docking_df["compound_name"].astype(str) == selected_compound]
    if len(sel_df) > 0:
        row = sel_df.iloc[0]
        affinity = row.get("vina_affinity_kcal_mol", np.nan)
        evidence = row.get("docking_evidence", "")

        evidence_tone = {"Strong": "good", "Moderate": "info", "Weak": "warn", "Failed": "bad"}.get(evidence, "neutral")
        render_badge_row([
            status_badge("Simulated fit score", "N/A" if pd.isna(affinity) else f"{affinity:.2f} kcal/mol",
                         "neutral", "A more negative value suggests a tighter predicted fit."),
            status_badge("Screening signal", evidence, evidence_tone,
                         "Strong ≤ -7.5 · Moderate ≤ -6.5 · Weak above that."),
        ])

        if evidence == "Strong":
            st.markdown(
                '<div style="background:#D1FAE5;border-left:4px solid #10B981;padding:10px 14px;border-radius:6px;">'
                "🟢 Strong simulated fit — this supports moving the candidate forward for laboratory review."
                "</div>",
                unsafe_allow_html=True,
            )
        elif evidence == "Moderate":
            st.info("🔵 Moderate simulated fit — useful as supporting evidence.")
        elif evidence == "Weak":
            st.warning("🟡 Weak simulated fit — the candidate needs stronger support elsewhere.")
        elif evidence == "Failed":
            st.error("🔴 Docking calculation failed.")

        pose_file = row.get("output_pose_pdbqt", "")
        if isinstance(pose_file, str) and pose_file.strip():
            with st.expander("🧬 View 3D binding pose"):
                render_docking_pose_3d(
                    receptor_pdb_path="data/5IU4_final_aligned.pdb",
                    ligand_pose_pdbqt_path=pose_file,
                    height=520,
                )
        else:
            st.caption("3D pose viewer is available only when using local docking.")

else:
    st.info("No docking results yet — upload a result or run local docking above.")

with st.expander("How to read the simulated-fit result"):
    st.markdown(
        """
        | Simulated score | Signal | What it means for screening |
        |------------------|---------------|---------|
        | **≤ -7.5 kcal/mol** | Strong | Supports higher priority for follow-up |
        | **-6.5 to -7.5 kcal/mol** | Moderate | Useful supporting evidence |
        | **> -6.5 kcal/mol** | Weak | Needs stronger support from other screens |

        > A more negative score suggests a tighter simulated fit. It does not prove that binding occurs in a biological system.
        """
    )
