import html

import streamlit as st
import pandas as pd
import numpy as np

from utils.ui_style import apply_poster_style, status_badge, render_badge_row, render_glossary_sidebar
from utils.molecule_drawer import render_molecule_2d
from utils.activity_screening import POSSIBLE_LABEL, PROMISING_LABEL, consensus_activity_points
from utils.consensus_presentation import (
    OUTCOME_BY_TIER,
    activity_signal_tone,
    format_activity_percentages,
    outcome_tone,
    outcome_for_tier,
)
from utils.auth import require_login, render_sidebar_user
from utils.wizard import render_wizard_sidebar


sb = require_login()
apply_poster_style()
render_sidebar_user(sb)
render_wizard_sidebar(current_step=5)
render_glossary_sidebar()


def build_signal_summary(row) -> str:
    """Compose one concise explanation of the three screening signals."""
    parts = []
    pred = row.get("ml_prediction", "")
    if pred == PROMISING_LABEL:
        parts.append("AI activity is promising")
    elif pred == POSSIBLE_LABEL:
        parts.append("AI activity is possible but uncertain")
    elif pred == "Predicted Inactive":
        parts.append("AI activity is weak")

    dock = row.get("docking_evidence", "")
    if dock == "Strong":
        parts.append("simulated fit is strong")
    elif dock == "Moderate":
        parts.append("simulated fit is moderate")
    elif dock == "Weak":
        parts.append("simulated fit is weak")

    drug = row.get("drug_likeness", "")
    if drug == "Favorable":
        parts.append("early developability has no major property flag")
    elif drug == "Borderline":
        parts.append("early developability needs review")
    elif drug == "Concern":
        parts.append("early developability raises a property concern")

    return "; ".join(parts) + "." if parts else "Evidence is currently limited."


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
    Build the shortlist to combine AI activity, simulated target fit, and early developability.
    The result shows a recommended next action and the evidence behind it.
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------- Generate ---------------

build_label = "↻ Rebuild candidate shortlist" if "consensus_df" in st.session_state else "▶ Build candidate shortlist"
if st.button(build_label, type="primary"):
    consensus_df = ml_df.copy()

    docking_cols = [c for c in ["compound_name", "vina_affinity_kcal_mol", "docking_evidence", "docking_note"]
                    if c in docking_df.columns]
    consensus_df = consensus_df.merge(docking_df[docking_cols], on="compound_name", how="left")

    drug_cols = [c for c in ["compound_name", "MW", "LogP", "TPSA", "HBD", "HBA",
                              "Rotatable Bonds", "drug_likeness_score", "minimum_property_score",
                              "drug_likeness"] if c in druglikeness_df.columns]
    consensus_df = consensus_df.merge(druglikeness_df[drug_cols], on="compound_name", how="left")

    scores, tiers, outcomes, recommendations, evidence_notes = [], [], [], [], []

    for _, row in consensus_df.iterrows():
        score = 0
        notes = []

        activity_points = consensus_activity_points(row.get("ml_prediction"))
        score += activity_points
        if activity_points == 2:
            notes.append("Promising AI signal")
        elif activity_points == 1:
            notes.append("Possible AI signal retained for supporting evidence")
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
            tier, rec = "Tier 1", "Move this candidate into laboratory confirmation first."
        elif score >= 3:
            tier, rec = "Tier 2", "Resolve the conflicting evidence before committing to laboratory testing."
        else:
            tier, rec = "Tier 3", "Defer or redesign before further testing."

        scores.append(score)
        tiers.append(tier)
        outcomes.append(OUTCOME_BY_TIER[tier])
        recommendations.append(rec)
        evidence_notes.append("; ".join(notes) if notes else "Insufficient evidence")

    consensus_df["consensus_score"] = scores
    consensus_df["consensus_tier"] = tiers
    consensus_df["screening_outcome"] = outcomes
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
    consensus_df = st.session_state["consensus_df"].copy()
    # Refresh presentation labels for results saved before a copy update.
    consensus_df["screening_outcome"] = consensus_df["consensus_tier"].map(OUTCOME_BY_TIER)

    # Tier summary
    t1 = int((consensus_df["consensus_tier"] == "Tier 1").sum())
    t2 = int((consensus_df["consensus_tier"] == "Tier 2").sum())
    t3 = int((consensus_df["consensus_tier"] == "Tier 3").sum())

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("🟢 Advance to lab validation", t1,
               help="The three screening signals provide the strongest combined support.")
    mc2.metric("🟡 Scientific review required", t2,
               help="Some signals support follow-up, but the case is incomplete or conflicting.")
    mc3.metric("⚪ Defer or redesign", t3,
               help="Current screening evidence does not support near-term laboratory priority.")

    # Decision-first comparison. Technical fields stay available below.
    display_cols = ["compound_name", "screening_outcome", "active_probability",
                    "docking_evidence", "drug_likeness", "recommendation"]
    display_cols = [column for column in display_cols if column in consensus_df.columns]
    shortlist_display = consensus_df[display_cols].copy()
    if "active_probability" in shortlist_display.columns:
        shortlist_display["active_probability"] = shortlist_display["active_probability"].apply(
            lambda value: format_activity_percentages(value)[0]
        )
    st.dataframe(
        shortlist_display.rename(columns={
            "compound_name": "Candidate",
            "screening_outcome": "Recommended outcome",
            "active_probability": "AI Active estimate",
            "docking_evidence": "Simulated fit",
            "drug_likeness": "Early developability",
            "recommendation": "Next action",
        }),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Show technical comparison table"):
        technical_cols = [
            "compound_name", "consensus_score", "consensus_tier", "active_probability",
            "ml_prediction", "applicability_domain", "vina_affinity_kcal_mol",
            "docking_evidence", "drug_likeness_score", "drug_likeness",
        ]
        technical_cols = [column for column in technical_cols if column in consensus_df.columns]
        st.dataframe(consensus_df[technical_cols], use_container_width=True, hide_index=True)

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
        tier = selected_row.get("consensus_tier", "")
        active_percent, inactive_percent = format_activity_percentages(
            selected_row.get("active_probability", np.nan)
        )
        outcome = outcome_for_tier(tier)
        tone = outcome_tone(tier)
        recommendation = html.escape(str(selected_row.get("recommendation", "")))
        signal_summary = html.escape(build_signal_summary(selected_row))

        st.markdown(
            f"""
            <div class="outcome-banner {tone}">
                <div class="outcome-label">Recommended next action</div>
                <div class="outcome-title">{html.escape(outcome)}</div>
                <div class="outcome-copy">{recommendation}<br><b>Why:</b> {signal_summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        dock = selected_row.get("docking_evidence", "N/A")
        drug = selected_row.get("drug_likeness", "N/A")
        drug_display = {"Favorable": "No major early flag", "Borderline": "Needs review",
                        "Concern": "Early concern"}.get(drug, drug)
        render_badge_row([
            status_badge(
                "AI activity estimate",
                f"Active {active_percent} · Inactive {inactive_percent}",
                activity_signal_tone(selected_row.get("active_probability", np.nan)),
                "Binary probability from the AI model in Step 2.",
            ),
            status_badge(
                "Simulated target fit",
                dock,
                {"Strong": "good", "Moderate": "warn", "Weak": "bad"}.get(dock, "neutral"),
                "Independent molecular-docking evidence.",
            ),
            status_badge(
                "Early developability",
                drug_display,
                {"Favorable": "good", "Borderline": "warn", "Concern": "bad"}.get(drug, "neutral"),
                "Basic molecular-property screen; not a safety assessment.",
            ),
        ])

        st.caption(
            "The Active/Inactive percentages are AI-model estimates only. The recommended action combines all three screens."
        )

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
            | AI activity signal is Promising | +2 |
            | AI activity signal is Possible | +1 |
            | Active probability ≥ 0.80 | +1 |
            | Inside Applicability Domain | +1 |
            | Docking Strong (≤ -7.5 kcal/mol) | +2 |
            | Docking Moderate (≤ -6.5 kcal/mol) | +1 |
            | Drug-likeness Favorable | +2 |
            | Drug-likeness Borderline | +1 |

            | Plain-language outcome | Internal tier | Score | What happens next |
            |------------------------|---------------|-------|-------------------|
            | **Advance to laboratory validation** | Tier 1 | ≥ 6 | Strongest combined support; test first |
            | **Scientific review required** | Tier 2 | 3–5 | Resolve conflicting signals before laboratory testing |
            | **Defer or redesign** | Tier 3 | < 3 | Do not prioritize for near-term testing |

            > The 0–8 combined score is not a probability. Active/Inactive percentages are generated only by the AI model in Step 2.
            > All outputs prioritize scientific follow-up; they are not proof of efficacy, safety, clinical success, or commercial value.
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
