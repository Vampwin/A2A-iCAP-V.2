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


sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=2)
render_glossary_sidebar()


st.title("🤖 Step 2: Screen for likely target activity")
st.caption("The AI looks for an early signal that each candidate may block the A₂A receptor.")

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
    <b>Decision question:</b> Which candidates show enough AI support to justify a second screening method?<br><br>
    Use the default setting, click <b>Run AI screen</b>, then review both the activity signal
    and the model-confidence label. Continue promising candidates to Step 3.
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- Run prediction ---------------

with st.expander("Advanced setting: Activity cutoff"):
    st.caption(
        "The default is appropriate for general screening. Raising the cutoff produces a shorter, more selective list."
    )
    custom_threshold = st.slider(
        "Minimum AI signal classified as promising",
        min_value=0.00, max_value=1.00, value=float(threshold), step=0.05,
    )

if st.button("▶ Run AI screen", type="primary"):
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
                 "Move to simulated-fit review", "Keep only with other strong evidence"),
    )

    invalid_mask = result_df["valid_smiles"] == False
    result_df.loc[invalid_mask, "ml_prediction"] = "Invalid SMILES"
    result_df.loc[invalid_mask, "active_probability"] = np.nan
    result_df.loc[invalid_mask, "applicability_domain"] = "Invalid SMILES"

    st.session_state["ml_result_df"] = result_df
    st.success("✅ AI screening complete — review the candidates below.")

st.divider()

# --------------- Show results ---------------

if "ml_result_df" in st.session_state:
    ml_result_df = st.session_state["ml_result_df"]

    # Summary table
    summary_cols = ["compound_name", "active_probability", "ml_prediction", "applicability_domain", "ml_note"]
    summary_cols = [c for c in summary_cols if c in ml_result_df.columns]
    summary_display = ml_result_df[summary_cols].copy()
    if "ml_prediction" in summary_display.columns:
        summary_display["ml_prediction"] = summary_display["ml_prediction"].replace({
            "Predicted Active": "Promising signal",
            "Predicted Inactive": "Weak signal",
        })
    if "applicability_domain" in summary_display.columns:
        summary_display["applicability_domain"] = summary_display["applicability_domain"].replace({
            "Inside AD": "Higher confidence",
            "Borderline AD": "Moderate confidence",
            "Outside AD": "Low confidence",
        })
    st.dataframe(
        summary_display.rename(columns={
            "compound_name": "Candidate",
            "active_probability": "AI activity signal",
            "ml_prediction": "Screening result",
            "applicability_domain": "Model confidence",
            "ml_note": "Suggested next step",
        }),
        use_container_width=True,
    )

    # Per-compound detail
    st.subheader("Candidate detail")
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
        pred_display = {
            "Predicted Active": "Promising signal",
            "Predicted Inactive": "Weak signal",
            "Invalid SMILES": "Unavailable",
        }.get(pred, pred)
        ad_display = {
            "Inside AD": "Higher confidence",
            "Borderline AD": "Moderate confidence",
            "Outside AD": "Low confidence",
            "Invalid SMILES": "Unavailable",
        }.get(ad, ad)

        render_badge_row([
            status_badge("AI activity signal", prob_display, prob_tone,
                         "Higher means the model sees a stronger activity signal."),
            status_badge("Screening result", pred_display, pred_tone,
                         "A simple pass-or-review label at the selected cutoff."),
            status_badge("Model confidence", ad_display, ad_tone,
                         "Confidence is higher when the molecule resembles examples used to train the model."),
        ])

        if pred == "Predicted Active":
            st.success("🟢 Promising AI signal — move to Step 3 for an independent simulation check.")
        elif pred == "Predicted Inactive":
            st.warning("🟡 Weak AI signal — keep only if there is another strong reason to investigate.")
        else:
            st.error("🔴 Invalid SMILES — prediction unavailable.")

        if ad == "Inside AD":
            st.success("🟢 Higher model confidence — this molecule is similar to the model's training examples.")
        elif ad == "Borderline AD":
            st.warning("🟡 Moderate model confidence — use this result as supporting evidence only.")
        elif ad == "Outside AD":
            st.error("🔴 Low model confidence — do not rely on the AI result alone.")

    # Collapsible extras
    with st.expander("Technical details: Why model confidence may be lower"):
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

    with st.expander("How to read the AI screening result"):
        st.markdown(
            """
            | Value | Meaning |
            |-------|---------|
            | **AI activity signal ≥ 0.70** | Stronger model support; suitable for the next screening step |
            | **AI activity signal 0.50–0.69** | Possible signal, with meaningful uncertainty |
            | **AI activity signal < 0.50** | Weak model support |
            | **Higher confidence** | Molecule is similar to the model's training examples |
            | **Moderate confidence** | Use the result as supporting evidence only |
            | **Low confidence** | Do not use the AI result alone for a decision |

            > This is a prioritization signal, not experimental confirmation of biological activity.
            """,
            unsafe_allow_html=True,
        )

    st.download_button(
        label="⬇ Download results (CSV)",
        data=ml_result_df.to_csv(index=False),
        file_name="a2a_ai_target_screen_results.csv",
        mime="text/csv",
    )

else:
    st.info("Click **Run AI screen** above to compare the candidates.")
