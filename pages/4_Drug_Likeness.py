import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors, Lipinski

from utils.molecule_drawer import render_molecule_2d
from utils.ui_style import apply_poster_style, render_glossary_sidebar
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=4)
render_glossary_sidebar()


st.title("📊 Step 4: Check early developability")
st.caption("Basic molecular properties can flag candidates that may be harder to develop before costly testing begins.")

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
    <div class="poster-box" style="border-left-color:#3A7D44; background:#F0FFF4;">
    <b>Decision question:</b> Do any basic molecular properties create an obvious early development concern?<br><br>
    Results are calculated automatically. Select a candidate, review the headline profile,
    then continue to Step 5 to combine all screening signals.
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- RDKit functions ---------------

def calculate_rdkit_properties(smiles):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return {
        "MW": Descriptors.MolWt(mol),
        "LogP": Crippen.MolLogP(mol),
        "TPSA": rdMolDescriptors.CalcTPSA(mol),
        "HBD": Lipinski.NumHDonors(mol),
        "HBA": Lipinski.NumHAcceptors(mol),
        "Rotatable Bonds": Lipinski.NumRotatableBonds(mol),
    }


def normalize_property(value, preferred_min, preferred_max, absolute_min, absolute_max):
    if value is None:
        return 0.0
    value = float(value)
    if preferred_min <= value <= preferred_max:
        return 1.0
    if value < preferred_min:
        return 0.0 if value <= absolute_min else round((value - absolute_min) / (preferred_min - absolute_min), 3)
    return 0.0 if value >= absolute_max else round((absolute_max - value) / (absolute_max - preferred_max), 3)


def normalize_rdkit_properties(props):
    return {
        "MW": normalize_property(props["MW"], 200, 500, 100, 700),
        "LogP": normalize_property(props["LogP"], 1, 5, -1, 7),
        "TPSA": normalize_property(props["TPSA"], 20, 120, 0, 160),
        "HBD": normalize_property(props["HBD"], 0, 5, 0, 8),
        "HBA": normalize_property(props["HBA"], 1, 10, 0, 14),
        "Rotatable Bonds": normalize_property(props["Rotatable Bonds"], 0, 8, 0, 12),
    }


def assign_drug_likeness(mean_score, min_score):
    if mean_score >= 0.80 and min_score >= 0.40:
        return "Favorable"
    elif mean_score >= 0.60:
        return "Borderline"
    else:
        return "Concern"


# --------------- Calculate ---------------

drug_rows = []
for _, row in compound_df.iterrows():
    smiles = row["canonical_smiles"]
    compound_name = row["compound_name"]
    props = calculate_rdkit_properties(smiles)

    if props is None:
        drug_rows.append({
            "compound_name": compound_name, "canonical_smiles": smiles,
            "MW": np.nan, "LogP": np.nan, "TPSA": np.nan,
            "HBD": np.nan, "HBA": np.nan, "Rotatable Bonds": np.nan,
            "drug_likeness_score": 0.0, "minimum_property_score": 0.0,
            "drug_likeness": "Invalid SMILES",
        })
    else:
        norm_props = normalize_rdkit_properties(props)
        scores = list(norm_props.values())
        mean_score = round(np.mean(scores), 3)
        min_score = round(np.min(scores), 3)
        drug_rows.append({
            "compound_name": compound_name, "canonical_smiles": smiles,
            "MW": round(props["MW"], 2), "LogP": round(props["LogP"], 2),
            "TPSA": round(props["TPSA"], 2), "HBD": props["HBD"],
            "HBA": props["HBA"], "Rotatable Bonds": props["Rotatable Bonds"],
            "MW_score": norm_props["MW"], "LogP_score": norm_props["LogP"],
            "TPSA_score": norm_props["TPSA"], "HBD_score": norm_props["HBD"],
            "HBA_score": norm_props["HBA"], "Rotatable_Bonds_score": norm_props["Rotatable Bonds"],
            "drug_likeness_score": mean_score, "minimum_property_score": min_score,
            "drug_likeness": assign_drug_likeness(mean_score, min_score),
        })

druglikeness_df = pd.DataFrame(drug_rows)
st.session_state["druglikeness_df"] = druglikeness_df

# --------------- Select compound ---------------

compound_list = druglikeness_df["compound_name"].astype(str).tolist()
selected_compound = st.selectbox("Select candidate", compound_list)
selected_row = druglikeness_df[druglikeness_df["compound_name"].astype(str) == selected_compound].iloc[0]

# --------------- Result card ---------------

dl = selected_row["drug_likeness"]
if dl == "Favorable":
    st.success(f"🟢 Early developability: **{dl}** — no major concern in this basic property screen.")
elif dl == "Borderline":
    st.warning(f"🟡 Early developability: **{dl}** — one or more properties deserve scientific review.")
elif dl == "Concern":
    st.error(f"🔴 Early developability: **{dl}** — the current structure may need optimization.")
else:
    st.error(f"❌ {dl}")

m1, m2 = st.columns(2)
m1.metric("Overall property fit", selected_row["drug_likeness_score"],
           help="Average of six early property checks, from 0 to 1. Higher indicates fewer basic developability flags.")
m2.metric("Weakest property", selected_row["minimum_property_score"],
           help="The lowest individual score. It highlights a specific issue that may be hidden by a good average.")

# --------------- Radar plot ---------------

properties = ["MW", "LogP", "TPSA", "HBD", "HBA", "Rotatable Bonds"]
plain_property_labels = ["Molecule size", "Fat/water balance", "Surface polarity",
                         "H-bond donors", "H-bond acceptors", "Flexibility"]
candidate_scores = [
    selected_row["MW_score"], selected_row["LogP_score"], selected_row["TPSA_score"],
    selected_row["HBD_score"], selected_row["HBA_score"], selected_row["Rotatable_Bonds_score"],
]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(r=candidate_scores, theta=plain_property_labels, fill="toself", name=selected_compound))
fig.add_trace(go.Scatterpolar(r=[1, 1, 1, 1, 1, 1], theta=plain_property_labels, fill="toself", name="Preferred range",
                               line=dict(dash="dot", color="gray")))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    showlegend=True, height=460,
    margin=dict(l=40, r=40, t=40, b=40),
)

col_struct, col_radar, col_table = st.columns([0.7, 1.2, 0.9])

with col_struct:
    st.markdown("**2D Structure**")
    render_molecule_2d(selected_row["canonical_smiles"], caption=selected_compound, width=330, height=250)

with col_radar:
    st.plotly_chart(fig, use_container_width=True)

PROPERTY_MEANINGS = {
    "MW": "Molecule size; very large molecules can be harder to absorb",
    "LogP": "Fat/water balance; an early indicator related to absorption",
    "TPSA": "Surface polarity; affects movement across cell membranes",
    "HBD": "Groups that donate hydrogen bonds; affects solubility and interactions",
    "HBA": "Groups that accept hydrogen bonds; affects solubility and interactions",
    "Rotatable Bonds": "Molecular flexibility; too much flexibility can complicate development",
}

with col_table:
    st.markdown("**Property values**")
    raw_table = pd.DataFrame({
        "Property": properties,
        "Meaning": [PROPERTY_MEANINGS[p] for p in properties],
        "Value": [selected_row["MW"], selected_row["LogP"], selected_row["TPSA"],
                  selected_row["HBD"], selected_row["HBA"], selected_row["Rotatable Bonds"]],
        "Score": candidate_scores,
    })
    st.dataframe(raw_table, use_container_width=True, hide_index=True)

# --------------- All compounds summary ---------------

with st.expander("Compare all candidates"):
    summary_cols = ["compound_name", "MW", "LogP", "TPSA", "HBD", "HBA",
                    "Rotatable Bonds", "drug_likeness_score", "drug_likeness"]
    st.dataframe(druglikeness_df[[c for c in summary_cols if c in druglikeness_df.columns]],
                 use_container_width=True)

with st.expander("How to read the early-developability result"):
    st.markdown(
        """
        Each radar axis shows how closely one basic property falls within the preferred screening range.
        A value closer to **1** means fewer concerns on that property.

        | Level | Condition | Meaning |
        |-------|-----------|---------|
        | **Favorable** | mean ≥ 0.80 and min ≥ 0.40 | No major concern in this basic screen |
        | **Borderline** | mean ≥ 0.60 | Some properties deserve review |
        | **Concern** | mean < 0.60 | Current structure may need optimization |

        > This screen does not assess safety, efficacy, metabolism, formulation, or clinical success.

        **Technical preferred ranges:** MW 200–500 Da · LogP 1–5 · TPSA 20–120 Å² · HBD ≤ 5 · HBA ≤ 10 · Rotatable Bonds ≤ 8
        """
    )
