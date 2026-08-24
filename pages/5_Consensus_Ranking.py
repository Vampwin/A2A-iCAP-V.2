import streamlit as st
import pandas as pd
import numpy as np

from utils.ui_style import apply_poster_style, status_badge, render_badge_row, render_glossary_sidebar
from utils.molecule_drawer import render_molecule_2d
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


st.set_page_config(page_title="Candidate Shortlist", page_icon="🏆", layout="wide")
sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=5)
render_glossary_sidebar()


def build_plain_verdict(row) -> str:
    """Compose a decision-focused takeaway from the three screening signals."""
    name = row.get("compound_name", "This compound")
    tier = row.get("consensus_tier", "")

    parts = []
    pred = row.get("ml_prediction", "")
    if pred == "Predicted Active":
        parts.append("the AI signal is promising")
    elif pred == "Predicted Inactive":
        parts.append("the AI signal is weak")

    dock = row.get("docking_evidence", "")
    if dock == "Strong":
        parts.append("the simulated fit is strong")
    elif dock == "Moderate":
        parts.append("the simulated fit is moderate")
    elif dock == "Weak":
        parts.append("the simulated fit is weak")

    drug = row.get("drug_likeness", "")
    if drug == "Favorable":
        parts.append("the early property profile is favorable")
    elif drug == "Borderline":
        parts.append("the early property profile needs review")
    elif drug == "Concern":
        parts.append("the early property profile raises concern")

    evidence_str = "; ".join(parts) if parts else "evidence is limited"
    tier_phrase = {
        "Tier 1": "supported for **earlier laboratory review**",
        "Tier 2": "supported for **secondary review**",
        "Tier 3": "best **deferred or redesigned**",
    }.get(tier, "not yet ranked")

    return f"{name} is {tier_phrase}: {evidence_str}."


st.title("🏆 Step 5: Build the candidate shortlist")
st.caption("Combine the three screening signals into a transparent recommendation for what to investigate next.")

# --------------- Guard ---------------

missing_items = []
if "ml_result_df" not in st.session_state:
    missing_items.append("Step 2: AI Target Screen")
if "docking_df" not in st.session_state:
    missing_items.append("Step 3: Simulated Target Fit")
if "druglikeness_df" not in st.session_state:
    missing_items.append("Step 4: Early Developability")

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
    <b>Decision question:</b> Which candidates have the strongest combined case for the next laboratory step?<br><br>
    Click <b>Build candidate shortlist</b>. The platform combines the AI signal,
    simulated target fit, and early developability profile—and shows why each candidate ranked where it did.
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- Generate ---------------

if st.button("▶ Build candidate shortlist", type="primary"):
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
            score += 2; notes.append("Promising AI signal")
        if pd.notna(row.get("active_probability")) and row.get("active_probability", 0) >= 0.80:
            score += 1; notes.append("Strong AI signal (≥ 0.80)")
        if row.get("applicability_domain") == "Inside AD":
            score += 1; notes.append("Higher model confidence")
        elif row.get("applicability_domain") == "Outside AD":
            notes.append("Low model confidence (caution)")

        if row.get("docking_evidence") == "Strong":
            score += 2; notes.append("Strong simulated fit")
        elif row.get("docking_evidence") == "Moderate":
            score += 1; notes.append("Moderate simulated fit")

        if row.get("drug_likeness") == "Favorable":
            score += 2; notes.append("Favorable early property profile")
        elif row.get("drug_likeness") == "Borderline":
            score += 1; notes.append("Early property profile needs review")

        if score >= 6:
            tier, rec = "Tier 1", "Review for laboratory confirmation first."
        elif score >= 3:
            tier, rec = "Tier 2", "Review after Tier 1 candidates or optimize the structure."
        else:
            tier, rec = "Tier 3", "Defer or redesign before further testing."

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
    st.success("✅ Shortlist ready — review the recommended next step for each candidate.")

st.divider()

# --------------- Show results ---------------

if "consensus_df" in st.session_state:
    consensus_df = st.session_state["consensus_df"]

    # Tier summary
    t1 = int((consensus_df["consensus_tier"] == "Tier 1").sum())
    t2 = int((consensus_df["consensus_tier"] == "Tier 2").sum())
    t3 = int((consensus_df["consensus_tier"] == "Tier 3").sum())

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("🥇 Test first", t1, help="Tier 1: the three screening signals provide the strongest combined support.")
    mc2.metric("🥈 Review next", t2, help="Tier 2: some signals support follow-up, but the case is incomplete.")
    mc3.metric("🥉 Defer or redesign", t3, help="Tier 3: limited support at this stage.")

    # Full results table
    display_cols = ["compound_name", "consensus_score", "consensus_tier",
                    "active_probability", "ml_prediction", "applicability_domain",
                    "vina_affinity_kcal_mol", "docking_evidence",
                    "drug_likeness_score", "drug_likeness", "recommendation"]
    rename_map = {"vina_affinity_kcal_mol": "affinity_kcal_mol"}
    display_cols = [c for c in display_cols if c in consensus_df.columns]
    shortlist_display = consensus_df[display_cols].copy()
    shortlist_display["ml_prediction"] = shortlist_display["ml_prediction"].replace({
        "Predicted Active": "Promising signal",
        "Predicted Inactive": "Weak signal",
    })
    shortlist_display["applicability_domain"] = shortlist_display["applicability_domain"].replace({
        "Inside AD": "Higher confidence",
        "Borderline AD": "Moderate confidence",
        "Outside AD": "Low confidence",
    })
    st.dataframe(
        shortlist_display.rename(columns={
            "compound_name": "Candidate",
            "consensus_score": "Combined score",
            "consensus_tier": "Priority tier",
            "active_probability": "AI activity signal",
            "ml_prediction": "AI screen",
            "applicability_domain": "Model confidence",
            "vina_affinity_kcal_mol": "Simulated fit score",
            "docking_evidence": "Fit signal",
            "drug_likeness_score": "Property fit",
            "drug_likeness": "Early developability",
            "recommendation": "Suggested next step",
        }),
        use_container_width=True,
    )

    st.divider()

    # Per-compound detail
    st.subheader("Candidate decision summary")
    selected_compound = st.selectbox("Select candidate", consensus_df["compound_name"].astype(str).tolist())
    selected_row = consensus_df[consensus_df["compound_name"].astype(str) == selected_compound].iloc[0]

    col_structure, col_summary = st.columns([0.7, 1.3])

    with col_structure:
        if "canonical_smiles" in selected_row and pd.notna(selected_row["canonical_smiles"]):
            render_molecule_2d(selected_row["canonical_smiles"], caption=selected_compound, width=340, height=260)

    with col_summary:
        st.markdown(f"##### {build_plain_verdict(selected_row)}")

        tier = selected_row.get("consensus_tier", "")
        tier_tone = {"Tier 1": "good", "Tier 2": "warn", "Tier 3": "neutral"}.get(tier, "neutral")
        render_badge_row([
            status_badge("Combined evidence score", selected_row.get("consensus_score", "N/A"), "info",
                         "Transparent score from the three screening signals (maximum 8 points)."),
            status_badge("Recommended priority", tier, tier_tone,
                         "Tier 1 = test first · Tier 2 = review next · Tier 3 = defer or redesign."),
        ])

        if tier == "Tier 1":
            st.success(f"🥇 {selected_row.get('recommendation', '')}")
        elif tier == "Tier 2":
            st.warning(f"🥈 {selected_row.get('recommendation', '')}")
        else:
            st.info(f"🥉 {selected_row.get('recommendation', '')}")

        st.markdown("**Why it ranked here:**")
        st.write(selected_row.get("evidence_summary", "—"))

        pred = selected_row.get("ml_prediction", "N/A")
        dock = selected_row.get("docking_evidence", "N/A")
        drug = selected_row.get("drug_likeness", "N/A")
        pred_display = {"Predicted Active": "Promising", "Predicted Inactive": "Weak"}.get(pred, pred)
        drug_display = {"Favorable": "No major early flag", "Borderline": "Needs review",
                        "Concern": "Early concern"}.get(drug, drug)
        render_badge_row([
            status_badge("AI activity screen", pred_display,
                         {"Predicted Active": "good", "Predicted Inactive": "warn"}.get(pred, "bad"),
                         "Whether the AI predicts A₂A receptor activity."),
            status_badge("Simulated target fit", dock,
                         {"Strong": "good", "Moderate": "info", "Weak": "warn"}.get(dock, "neutral"),
                         "How tightly the compound binds the receptor, from docking."),
            status_badge("Early developability", drug_display,
                         {"Favorable": "good", "Borderline": "warn", "Concern": "bad"}.get(drug, "neutral"),
                         "Whether its physicochemical properties suit an oral drug."),
        ])

    # Evidence streams detail (collapsed)
    with st.expander("Technical details: Evidence behind the shortlist"):
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            st.markdown("**AI activity screen**")
            ml_disp = ["compound_name", "active_probability", "ml_prediction", "applicability_domain"]
            st.dataframe(ml_df[[c for c in ml_disp if c in ml_df.columns]], use_container_width=True)
        with ec2:
            st.markdown("**Simulated target fit**")
            dock_disp = ["compound_name", "vina_affinity_kcal_mol", "docking_evidence"]
            dock_show = docking_df[[c for c in dock_disp if c in docking_df.columns]].rename(
                columns={"vina_affinity_kcal_mol": "affinity_kcal_mol"}
            )
            st.dataframe(dock_show, use_container_width=True)
        with ec3:
            st.markdown("**Early developability**")
            drug_disp = ["compound_name", "drug_likeness_score", "drug_likeness"]
            st.dataframe(druglikeness_df[[c for c in drug_disp if c in druglikeness_df.columns]], use_container_width=True)

    with st.expander("Technical details: Scoring rules and interpretation"):
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
            | **Tier 1** | ≥ 6 | Strongest combined support — review for laboratory confirmation first |
            | **Tier 2** | 3–5 | Partial support — review after Tier 1 or optimize the structure |
            | **Tier 3** | < 3 | Limited support — defer or redesign |

            > The shortlist prioritizes scientific follow-up. It is not proof of efficacy, safety, clinical success, or commercial value.
            """
        )

    st.download_button(
        label="⬇ Download candidate shortlist (CSV)",
        data=consensus_df.to_csv(index=False),
        file_name="a2a_candidate_shortlist.csv",
        mime="text/csv",
    )

else:
    st.info("Click **Build candidate shortlist** above to combine the screening results.")
