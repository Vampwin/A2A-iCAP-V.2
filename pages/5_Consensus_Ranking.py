import streamlit as st
import pandas as pd
import numpy as np

from utils.ui_style import apply_poster_style, status_badge, render_badge_row, render_glossary_sidebar
from utils.molecule_drawer import render_molecule_2d_bw
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


st.set_page_config(page_title="Consensus Ranking", page_icon="🏆", layout="wide")
sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=5)
render_glossary_sidebar()


def build_plain_verdict(row) -> str:
    """Compose a single plain-English takeaway sentence from the 3 evidence streams."""
    name = row.get("compound_name", "This compound")
    tier = row.get("consensus_tier", "")

    parts = []
    pred = row.get("ml_prediction", "")
    if pred == "Predicted Active":
        parts.append("the AI predicts it's active")
    elif pred == "Predicted Inactive":
        parts.append("the AI predicts it's inactive")

    dock = row.get("docking_evidence", "")
    if dock == "Strong":
        parts.append("docking shows strong binding")
    elif dock == "Moderate":
        parts.append("docking shows moderate binding")
    elif dock == "Weak":
        parts.append("docking shows weak binding")

    drug = row.get("drug_likeness", "")
    if drug == "Favorable":
        parts.append("drug-likeness is favorable")
    elif drug == "Borderline":
        parts.append("drug-likeness is borderline")
    elif drug == "Concern":
        parts.append("drug-likeness raises concern")

    evidence_str = "; ".join(parts) if parts else "evidence is limited"
    tier_phrase = {
        "Tier 1": "a **high-priority** candidate",
        "Tier 2": "a **moderate-priority** candidate",
        "Tier 3": "a **low-priority** candidate",
    }.get(tier, "not yet ranked")

    return f"{name} is {tier_phrase}: {evidence_str}."


st.title("🏆 Step 5: Consensus Ranking")

# --------------- Guard ---------------

missing_items = []
if "ml_result_df" not in st.session_state:
    missing_items.append("Step 2: ML Prediction")
if "docking_df" not in st.session_state:
    missing_items.append("Step 3: Docking Evidence")
if "druglikeness_df" not in st.session_state:
    missing_items.append("Step 4: Drug-Likeness")

if missing_items:
    st.warning("⬅️ Please complete these steps first:")
    for item in missing_items:
        st.write(f"- {item}")
    st.stop()

ml_df = st.session_state["ml_result_df"].copy()
docking_df = st.session_state["docking_df"].copy()
druglikeness_df = st.session_state["druglikeness_df"].copy()

# --------------- Action box ---------------

st.markdown(
    """
    <div class="poster-box" style="border-left-color:#C9A84C; background:#FFFDF0;">
    <b>What to do on this page:</b><br>
    1. Click <b>Generate Consensus Ranking</b> below<br>
    2. The platform combines AI prediction + docking + drug-likeness scores<br>
    3. Each compound receives a <b>Tier 1</b> (high), <b>Tier 2</b> (moderate), or <b>Tier 3</b> (low) priority
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- Generate ---------------

if st.button("▶ Generate Consensus Ranking", type="primary"):
    consensus_df = ml_df.copy()

    docking_cols = [c for c in ["compound_name", "vina_affinity_kcal_mol", "docking_evidence", "docking_note"]
                    if c in docking_df.columns]
    consensus_df = consensus_df.merge(docking_df[docking_cols], on="compound_name", how="left")

    drug_cols = [c for c in ["compound_name", "MW", "LogP", "TPSA", "HBD", "HBA",
                              "Rotatable Bonds", "drug_likeness_score", "minimum_property_score",
                              "drug_likeness"] if c in druglikeness_df.columns]
    consensus_df = consensus_df.merge(druglikeness_df[drug_cols], on="compound_name", how="left")

    scores, tiers, recommendations, evidence_notes = [], [], [], []

    for _, row in consensus_df.iterrows():
        score = 0
        notes = []

        if row.get("ml_prediction") == "Predicted Active":
            score += 2; notes.append("AI predicts Active")
        if pd.notna(row.get("active_probability")) and row.get("active_probability", 0) >= 0.80:
            score += 1; notes.append("Probability ≥ 0.80")
        if row.get("applicability_domain") == "Inside AD":
            score += 1; notes.append("Inside AD")
        elif row.get("applicability_domain") == "Outside AD":
            notes.append("Outside AD (caution)")

        if row.get("docking_evidence") == "Strong":
            score += 2; notes.append("Docking Strong")
        elif row.get("docking_evidence") == "Moderate":
            score += 1; notes.append("Docking Moderate")

        if row.get("drug_likeness") == "Favorable":
            score += 2; notes.append("Drug-likeness Favorable")
        elif row.get("drug_likeness") == "Borderline":
            score += 1; notes.append("Drug-likeness Borderline")

        if score >= 6:
            tier, rec = "Tier 1", "High-priority — recommend experimental confirmation."
        elif score >= 3:
            tier, rec = "Tier 2", "Moderate priority — consider after Tier 1 compounds."
        else:
            tier, rec = "Tier 3", "Low priority — structural modification may be needed."

        scores.append(score)
        tiers.append(tier)
        recommendations.append(rec)
        evidence_notes.append("; ".join(notes) if notes else "Insufficient evidence")

    consensus_df["consensus_score"] = scores
    consensus_df["consensus_tier"] = tiers
    consensus_df["recommendation"] = recommendations
    consensus_df["evidence_summary"] = evidence_notes

    sort_cols, asc_list = ["consensus_score"], [False]
    if "vina_affinity_kcal_mol" in consensus_df.columns:
        sort_cols.append("vina_affinity_kcal_mol"); asc_list.append(True)

    consensus_df = consensus_df.sort_values(by=sort_cols, ascending=asc_list).reset_index(drop=True)
    st.session_state["consensus_df"] = consensus_df
    st.success("✅ Ranking complete — results shown below.")

st.divider()

# --------------- Show results ---------------

if "consensus_df" in st.session_state:
    consensus_df = st.session_state["consensus_df"]

    # Tier summary
    t1 = int((consensus_df["consensus_tier"] == "Tier 1").sum())
    t2 = int((consensus_df["consensus_tier"] == "Tier 2").sum())
    t3 = int((consensus_df["consensus_tier"] == "Tier 3").sum())

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("🥇 Tier 1 — High priority", t1, help="Score ≥ 6 — all 3 evidence streams align.")
    mc2.metric("🥈 Tier 2 — Moderate priority", t2, help="Score 3–5 — partial evidence.")
    mc3.metric("🥉 Tier 3 — Low priority", t3, help="Score < 3 — weak evidence, likely needs structural changes.")

    # Full results table
    display_cols = ["compound_name", "consensus_score", "consensus_tier",
                    "active_probability", "ml_prediction", "applicability_domain",
                    "vina_affinity_kcal_mol", "docking_evidence",
                    "drug_likeness_score", "drug_likeness", "recommendation"]
    rename_map = {"vina_affinity_kcal_mol": "affinity_kcal_mol"}
    display_cols = [c for c in display_cols if c in consensus_df.columns]
    st.dataframe(
        consensus_df[display_cols].rename(columns={"vina_affinity_kcal_mol": "affinity_kcal_mol"}),
        use_container_width=True,
    )

    st.divider()

    # Per-compound detail
    st.subheader("Compound Detail")
    selected_compound = st.selectbox("Select compound", consensus_df["compound_name"].astype(str).tolist())
    selected_row = consensus_df[consensus_df["compound_name"].astype(str) == selected_compound].iloc[0]

    col_structure, col_summary = st.columns([0.7, 1.3])

    with col_structure:
        if "canonical_smiles" in selected_row and pd.notna(selected_row["canonical_smiles"]):
            render_molecule_2d_bw(selected_row["canonical_smiles"], caption=selected_compound, width=280, height=220)

    with col_summary:
        st.markdown(f"##### {build_plain_verdict(selected_row)}")

        tier = selected_row.get("consensus_tier", "")
        tier_tone = {"Tier 1": "good", "Tier 2": "warn", "Tier 3": "neutral"}.get(tier, "neutral")
        render_badge_row([
            status_badge("Consensus Score", selected_row.get("consensus_score", "N/A"), "info",
                         "Combined score from AI + docking + drug-likeness (max 8 points)."),
            status_badge("Consensus Tier", tier, tier_tone,
                         "Overall priority ranking based on the consensus score."),
        ])

        if tier == "Tier 1":
            st.success(f"🥇 {selected_row.get('recommendation', '')}")
        elif tier == "Tier 2":
            st.warning(f"🥈 {selected_row.get('recommendation', '')}")
        else:
            st.info(f"🥉 {selected_row.get('recommendation', '')}")

        st.markdown("**Supporting evidence:**")
        st.write(selected_row.get("evidence_summary", "—"))

        pred = selected_row.get("ml_prediction", "N/A")
        dock = selected_row.get("docking_evidence", "N/A")
        drug = selected_row.get("drug_likeness", "N/A")
        render_badge_row([
            status_badge("AI Prediction", pred,
                         {"Predicted Active": "good", "Predicted Inactive": "warn"}.get(pred, "bad"),
                         "Whether the AI predicts A₂A receptor activity."),
            status_badge("Docking", dock,
                         {"Strong": "good", "Moderate": "info", "Weak": "warn"}.get(dock, "neutral"),
                         "How tightly the compound binds the receptor, from docking."),
            status_badge("Drug-likeness", drug,
                         {"Favorable": "good", "Borderline": "warn", "Concern": "bad"}.get(drug, "neutral"),
                         "Whether its physicochemical properties suit an oral drug."),
        ])

    # Evidence streams detail (collapsed)
    with st.expander("Evidence streams detail"):
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            st.markdown("**AI Prediction**")
            ml_disp = ["compound_name", "active_probability", "ml_prediction", "applicability_domain"]
            st.dataframe(ml_df[[c for c in ml_disp if c in ml_df.columns]], use_container_width=True)
        with ec2:
            st.markdown("**Docking**")
            dock_disp = ["compound_name", "vina_affinity_kcal_mol", "docking_evidence"]
            dock_show = docking_df[[c for c in dock_disp if c in docking_df.columns]].rename(
                columns={"vina_affinity_kcal_mol": "affinity_kcal_mol"}
            )
            st.dataframe(dock_show, use_container_width=True)
        with ec3:
            st.markdown("**Drug-Likeness**")
            drug_disp = ["compound_name", "drug_likeness_score", "drug_likeness"]
            st.dataframe(druglikeness_df[[c for c in drug_disp if c in druglikeness_df.columns]], use_container_width=True)

    with st.expander("📖 Scoring criteria & interpretation"):
        st.markdown(
            """
            **Scoring rules (max 8 points):**

            | Condition | Points |
            |-----------|--------|
            | AI predicts Active | +2 |
            | Active probability ≥ 0.80 | +1 |
            | Inside Applicability Domain | +1 |
            | Docking Strong (≤ -7.5 kcal/mol) | +2 |
            | Docking Moderate (≤ -6.5 kcal/mol) | +1 |
            | Drug-likeness Favorable | +2 |
            | Drug-likeness Borderline | +1 |

            | Tier | Score | Recommendation |
            |------|-------|----------------|
            | **Tier 1** | ≥ 6 | All 3 evidence streams align — proceed to lab confirmation |
            | **Tier 2** | 3–5 | Partial evidence — consider after Tier 1 or optimise structure |
            | **Tier 3** | < 3 | Weak evidence — structural modification needed |

            > All results are computational estimates. Experimental validation is required.
            """
        )

    st.download_button(
        label="⬇ Download Consensus Ranking (CSV)",
        data=consensus_df.to_csv(index=False),
        file_name="a2a_consensus_ranking_results.csv",
        mime="text/csv",
    )

else:
    st.info("Click **Generate Consensus Ranking** above to see results.")
