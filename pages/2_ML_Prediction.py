import os
import json
import joblib

import streamlit as st
import pandas as pd
import numpy as np

from utils.ui_style import apply_poster_style, status_badge, render_badge_row, render_glossary_sidebar
from utils.ml_features import calculate_ml_features_from_smiles
from utils.molecule_drawer import render_molecule_2d
from utils.ad_assessment import assess_applicability_domain_for_features
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


st.set_page_config(page_title="ML Prediction", page_icon="🤖", layout="wide")
sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=2)
render_glossary_sidebar()


st.title("🤖 Step 2: AI Activity Prediction")

# --------------- Load model ---------------

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "final_model.pkl")
FEATURE_NAMES_PATH = os.path.join(MODEL_DIR, "feature_names.pkl")
THRESHOLD_PATH = os.path.join(MODEL_DIR, "threshold.json")
AD_REFERENCE_PATH = os.path.join(MODEL_DIR, "ad_reference.json")


@st.cache_resource
def _load_model_artifacts():
    model = joblib.load(MODEL_PATH)
    feature_names = joblib.load(FEATURE_NAMES_PATH)
    with open(THRESHOLD_PATH, "r", encoding="utf-8") as f:
        threshold_data = json.load(f)
    with open(AD_REFERENCE_PATH, "r", encoding="utf-8") as f:
        ad_reference = json.load(f)
    threshold = threshold_data.get("active_probability_threshold", 0.50)
    return model, feature_names, threshold, threshold_data, ad_reference


required_files = [MODEL_PATH, FEATURE_NAMES_PATH, THRESHOLD_PATH, AD_REFERENCE_PATH]
missing_files = [f for f in required_files if not os.path.exists(f)]
if missing_files:
    st.error("Model files not found — please ensure the models/ folder contains all required files.")
    st.stop()

model, feature_names, threshold, threshold_data, ad_reference = _load_model_artifacts()

# --------------- Guard: need compound data ---------------

if "compound_df" not in st.session_state:
    st.warning("⬅️ No compounds loaded yet — please complete **Step 1: Compound Input** first.")
    st.stop()

compound_df = st.session_state["compound_df"].copy()
if "compound_name" not in compound_df.columns:
    compound_df["compound_name"] = compound_df["input_value"].astype(str)

# --------------- Action box ---------------

st.markdown(
    """
    <div class="poster-box" style="border-left-color:#1B6B6B; background:#F0FAFA;">
    <b>What to do on this page:</b><br>
    1. (Optional) Adjust the threshold slider below<br>
    2. Click <b>Run ML prediction</b> — the AI will analyse all your compounds<br>
    3. Review the results table and per-compound scores<br>
    4. Then go to <b>Step 3: Docking Evidence</b> in the sidebar
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- Run prediction ---------------

custom_threshold = st.slider(
    "Prediction threshold (compounds with probability ≥ this are classified as Active)",
    min_value=0.00, max_value=1.00, value=float(threshold), step=0.05,
)

if st.button("▶ Run ML prediction", type="primary"):
    smiles_list = compound_df["canonical_smiles"].astype(str).tolist()
    X_model, valid_smiles = calculate_ml_features_from_smiles(
        smiles_list=smiles_list, feature_names=feature_names,
    )

    if X_model.shape[1] != len(feature_names):
        st.error("Feature mismatch — please check the SMILES strings.")
        st.stop()

    proba_matrix = model.predict_proba(X_model)
    active_class_label = threshold_data.get("active_class_label", 1)
    if hasattr(model, "classes_") and active_class_label in list(model.classes_):
        active_class_index = list(model.classes_).index(active_class_label)
    else:
        active_class_index = 1

    probability = proba_matrix[:, active_class_index]
    prediction = np.where(probability >= custom_threshold, "Predicted Active", "Predicted Inactive")
    ad_df = assess_applicability_domain_for_features(X_model=X_model, ad_reference=ad_reference)

    result_df = compound_df.copy()
    result_df["valid_smiles"] = valid_smiles.values
    result_df["active_probability"] = np.round(probability, 4)
    result_df["ml_prediction"] = prediction
    result_df["applicability_domain"] = ad_df["applicability_domain"].values
    result_df["ad_inside_ratio"] = ad_df["ad_inside_ratio"].values
    result_df["ad_features_checked"] = ad_df["ad_features_checked"].values
    result_df["ad_outside_features_count"] = ad_df["ad_outside_features_count"].values
    result_df["ad_outside_features_preview"] = ad_df["ad_outside_features_preview"].values
    result_df["ml_note"] = np.where(
        result_df["valid_smiles"] == False, "Invalid SMILES",
        np.where(result_df["ml_prediction"] == "Predicted Active",
                 "Consider proceeding to docking", "Low priority"),
    )

    invalid_mask = result_df["valid_smiles"] == False
    result_df.loc[invalid_mask, "ml_prediction"] = "Invalid SMILES"
    result_df.loc[invalid_mask, "active_probability"] = np.nan
    result_df.loc[invalid_mask, "applicability_domain"] = "Invalid SMILES"

    st.session_state["ml_result_df"] = result_df
    st.success("✅ Prediction complete — results shown below.")

st.divider()

# --------------- Show results ---------------

if "ml_result_df" in st.session_state:
    ml_result_df = st.session_state["ml_result_df"]

    # Summary table
    summary_cols = ["compound_name", "active_probability", "ml_prediction", "applicability_domain", "ml_note"]
    summary_cols = [c for c in summary_cols if c in ml_result_df.columns]
    st.dataframe(ml_result_df[summary_cols], use_container_width=True)

    # Per-compound detail
    st.subheader("Compound Detail")
    selected_compound = st.selectbox(
        "Select compound",
        ml_result_df["compound_name"].astype(str).tolist(),
    )
    selected_result = ml_result_df[ml_result_df["compound_name"].astype(str) == selected_compound].iloc[0]

    col_struct, col_scores = st.columns([0.7, 1.3])

    with col_struct:
        smiles_val = selected_result.get("canonical_smiles", "")
        if pd.notna(smiles_val) and str(smiles_val).strip():
            render_molecule_2d(smiles_val, caption=selected_compound, width=340, height=260)

    with col_scores:
        pred = selected_result["ml_prediction"]
        ad = selected_result["applicability_domain"]
        prob_val = selected_result["active_probability"]

        if pd.isna(prob_val):
            prob_display, prob_tone = "N/A", "neutral"
        else:
            prob_display = f"{prob_val:.2f} ({prob_val * 100:.0f}%)"
            prob_tone = "good" if prob_val >= 0.70 else ("warn" if prob_val >= 0.50 else "bad")

        pred_tone = {"Predicted Active": "good", "Predicted Inactive": "warn"}.get(pred, "bad")
        ad_tone = {"Inside AD": "good", "Borderline AD": "warn", "Outside AD": "bad"}.get(ad, "neutral")

        render_badge_row([
            status_badge("Active Probability", prob_display, prob_tone,
                          "AI confidence the compound blocks the A₂A receptor. Higher = more confident."),
            status_badge("Prediction", pred, pred_tone,
                         "The AI's activity call at the current threshold."),
            status_badge("Applicability Domain", ad, ad_tone,
                         "How trustworthy this prediction is, based on similarity to the AI's training data."),
        ])

        if pred == "Predicted Active":
            st.success("🟢 Predicted Active — recommended to proceed with docking.")
        elif pred == "Predicted Inactive":
            st.warning("🟡 Predicted Inactive.")
        else:
            st.error("🔴 Invalid SMILES — prediction unavailable.")

        if ad == "Inside AD":
            st.success("🟢 Inside Applicability Domain — reliable prediction.")
        elif ad == "Borderline AD":
            st.warning("🟡 Borderline AD — moderate uncertainty.")
        elif ad == "Outside AD":
            st.error("🔴 Outside AD — interpret with caution.")

    # Collapsible extras
    with st.expander("AD feature details"):
        m4, m5, m6 = st.columns(3)
        m4.metric("AD Inside Ratio", selected_result.get("ad_inside_ratio", "N/A"),
                   help="Share of molecular descriptors that fall inside the AI's trained range (0–1, higher = more trustworthy).")
        m5.metric("Features Checked", selected_result.get("ad_features_checked", "N/A"),
                   help="Number of molecular descriptors compared against the training data.")
        m6.metric("Outside Features", selected_result.get("ad_outside_features_count", "N/A"),
                   help="Number of descriptors that fall outside the AI's trained range.")
        outside_preview = selected_result.get("ad_outside_features_preview", "")
        if isinstance(outside_preview, str) and outside_preview.strip():
            st.write(outside_preview)

    with st.expander("📖 How to read these results"):
        st.markdown(
            """
            | Value | Meaning |
            |-------|---------|
            | **Active Probability ≥ 0.70** | High likelihood of A<sub>2A</sub> antagonist activity |
            | **Active Probability 0.50–0.69** | Possible, but uncertain |
            | **Active Probability < 0.50** | Low likelihood |
            | **Inside AD** | Reliable prediction — compound is within the model's training space |
            | **Borderline AD** | Near boundary — use as supporting evidence only |
            | **Outside AD** | Outside training space — interpret with caution |

            > This model has been developed and validated specifically for A<sub>2A</sub> receptor antagonist prediction.
            """,
            unsafe_allow_html=True,
        )

    st.download_button(
        label="⬇ Download results (CSV)",
        data=ml_result_df.to_csv(index=False),
        file_name="a2a_ml_prediction_results.csv",
        mime="text/csv",
    )

else:
    st.info("Click **Run ML prediction** above to see results here.")
