"""
Regenerate the published A2A-iCAP screening numbers from the raw source files.

Every headline figure in the project report and technical abstract is produced
by this script from three primary workbooks plus the GNINA pose table. Nothing
is read from a spreadsheet summary sheet, so a reviewer can confirm the claims
independently.

    python scripts/verify_consensus.py --data-root "<Poster Preparation Material>" \
        --json docs/consensus_verification_results.json

The script also re-derives the best docking pose per ligand from the full
5,424-pose table rather than trusting the pre-computed BestPose sheet, and
reports any disagreement.

Expected output (ML confidence cut-off 0.70):

    Tier 1 Strict             35
    Tier 2 Relaxed AD         21
    Tier 3 Docking+Druglike  129
    Combined final hits      185
    External test set: BA 0.8927, MCC 0.7841, n = 939
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.simplefilter("ignore")

try:
    import openpyxl
except ImportError:  # pragma: no cover
    sys.exit("openpyxl is required: pip install openpyxl")

# Published selection criteria. Changing any of these invalidates the tier
# counts quoted in the report.
CNN_POSE_MIN = 0.65        # GNINA CNN pose-quality threshold
AFFINITY_MAX = -7.4        # GNINA docking affinity, kcal/mol
ML_CONFIDENCE_MIN = 0.70   # Random Forest confidence for Tier 1 and Tier 2
LIPINSKI = {"AMW": 500, "SlogP": 5, "NumHBD": 5, "NumHBA": 10}
VEBER = {"TPSA": 140, "NumRotatableBonds": 10}

REL_GNINA = "GNINA Docking/results_5IU4_MCENPL/gnina_report_5IU4_MCENPL.xlsx"
REL_DRUGLIKE = "Drug Likeness/Drug-Likeness from RDkit properties_AS.xlsx"
REL_ML = "ML-Classification/ML_Classification_Prediction_Results.xlsx"
REL_TESTSET = "ML-Classification/Test set prediction.xlsx"

_ID = re.compile(r"(MCENPL\d+)")


def compound_id(value):
    """Reduce a ligand label such as MCENPL000051__state1 to its parent ID."""
    if value is None:
        return None
    m = _ID.search(str(value))
    return m.group(1) if m else None


def read_sheet(path, sheet=None):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    # strict=False: read-only sheets can yield ragged rows.
    records = [dict(zip(header, r, strict=False)) for r in rows
               if any(v is not None for v in r)]
    wb.close()
    return records


def load_docking(root):
    path = root / REL_GNINA
    all_poses = read_sheet(path, "AllPoses")
    best_sheet = read_sheet(path, "BestPose")

    reported = {}
    for row in best_sheet:
        cid = compound_id(row["ligand"])
        if cid:
            reported[cid] = row

    # Independently re-derive the best pose: highest CNN pose score per ligand.
    derived = {}
    for row in all_poses:
        cid, score = compound_id(row["ligand"]), row["cnn_pose_score"]
        if cid is None or score is None:
            continue
        if cid not in derived or score > derived[cid]["cnn_pose_score"]:
            derived[cid] = row

    mismatches = [
        cid for cid in derived
        if cid in reported
        and abs((derived[cid]["cnn_pose_score"] or 0.0)
                - (reported[cid]["cnn_pose_score"] or 0.0)) > 1e-9
    ]
    return derived, {
        "all_pose_rows": len(all_poses),
        "best_pose_rows": len(best_sheet),
        "unique_ligands": len(derived),
        "best_pose_mismatches": len(mismatches),
    }


def load_druglikeness(root):
    out = {}
    for row in read_sheet(root / REL_DRUGLIKE):
        cid = compound_id(row["Compound"])
        if cid is None:
            continue
        lip = all(row[k] <= v for k, v in LIPINSKI.items())
        veb = all(row[k] <= v for k, v in VEBER.items())
        out[cid] = {"lipinski": lip, "veber": veb, "combined": lip and veb}
    return out


def load_ml(root):
    out = {}
    for row in read_sheet(root / REL_ML):
        cid = compound_id(row["Compound"])
        if cid is None:
            continue
        out[cid] = {
            "prediction": str(row["Prediction (activity)"]).strip().lower(),
            "confidence": row["Prediction (activity) (Confidence)"],
            "ad_status": str(row["Prediction"]).strip().lower(),
            "apd": row["APD"],
        }
    return out


def score_test_set(root):
    """Recompute held-out external test-set metrics from the raw predictions."""
    path = root / REL_TESTSET
    if not path.exists():
        return None
    rows = read_sheet(path)
    c = Counter((str(r.get("activity")).strip(),
                 str(r.get("Prediction (activity)")).strip()) for r in rows)
    tp, fn = c[("Active", "Active")], c[("Active", "Inactive")]
    tn, fp = c[("Inactive", "Inactive")], c[("Inactive", "Active")]
    n = tp + fn + tn + fp
    if n == 0:
        return None
    sens, spec = tp / (tp + fn), tn / (tn + fp)
    prec = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * prec * sens / (prec + sens) if prec + sens else 0.0
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {"n": n, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "balanced_accuracy": (sens + spec) / 2, "accuracy": (tp + tn) / n,
            "sensitivity": sens, "specificity": spec, "f1": f1,
            "mcc": ((tp * tn - fp * fn) / den) if den else 0.0}


def build_consensus(docking, druglike, ml, confidence_min=ML_CONFIDENCE_MIN):
    docking_pass = {
        cid for cid, r in docking.items()
        if r["cnn_pose_score"] is not None and r["affinity_kcal_mol"] is not None
        and r["cnn_pose_score"] >= CNN_POSE_MIN
        and r["affinity_kcal_mol"] <= AFFINITY_MAX
    }
    tier1, tier2_cum, tier3_cum = [], [], []
    for cid in sorted(docking_pass):
        if not druglike.get(cid, {}).get("combined"):
            continue
        tier3_cum.append(cid)                        # Consensus 3
        rec = ml.get(cid)
        if not rec or rec["prediction"] != "active":
            continue
        if (rec["confidence"] or 0.0) < confidence_min:
            continue
        tier2_cum.append(cid)                        # Consensus 2
        if rec["ad_status"] == "reliable":
            tier1.append(cid)                        # Consensus 1
    return {
        "docking_pass": len(docking_pass),
        "consensus_1_strict": len(tier1),
        "consensus_2_relaxed_ad": len(tier2_cum),
        "consensus_3_docking_druglike": len(tier3_cum),
        "tier_1": len(tier1),
        "tier_2": len(tier2_cum) - len(tier1),
        "tier_3": len(tier3_cum) - len(tier2_cum),
        "combined_final_hits": len(tier3_cum),
        "tier_1_compounds": tier1,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Verify A2A-iCAP screening numbers from raw source files.")
    ap.add_argument("--data-root", required=True, type=Path,
                    help="folder containing 'GNINA Docking', 'Drug Likeness' "
                         "and 'ML-Classification'")
    ap.add_argument("--confidence-min", type=float, default=ML_CONFIDENCE_MIN)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not args.data_root.is_dir():
        print("ERROR: --data-root not found: {}".format(args.data_root))
        return 2

    docking, dock_stats = load_docking(args.data_root)
    druglike = load_druglikeness(args.data_root)
    ml = load_ml(args.data_root)
    consensus = build_consensus(docking, druglike, ml, args.confidence_min)
    metrics = score_test_set(args.data_root)
    docked = [c for c in druglike if c in docking]

    report = {
        "criteria": {"cnn_pose_min": CNN_POSE_MIN,
                     "affinity_max_kcal_mol": AFFINITY_MAX,
                     "ml_confidence_min": args.confidence_min,
                     "lipinski": LIPINSKI, "veber": VEBER},
        "docking": dict(
            dock_stats,
            cnn_ge_065=sum(1 for r in docking.values()
                           if (r["cnn_pose_score"] or -9) >= 0.65),
            cnn_ge_080=sum(1 for r in docking.values()
                           if (r["cnn_pose_score"] or -9) >= 0.80),
            affinity_le_74=sum(1 for r in docking.values()
                               if (r["affinity_kcal_mol"] or 99) <= -7.4),
            positive_affinity_outliers=sum(
                1 for r in docking.values() if (r["affinity_kcal_mol"] or -99) > 0)),
        "druglikeness": {
            "rows": len(druglike),
            "lipinski_pass": sum(v["lipinski"] for v in druglike.values()),
            "veber_pass": sum(v["veber"] for v in druglike.values()),
            "combined_pass": sum(v["combined"] for v in druglike.values()),
            "matched_to_docked_set": len(docked),
            "lipinski_pass_in_docked_set": sum(druglike[c]["lipinski"] for c in docked),
            "veber_pass_in_docked_set": sum(druglike[c]["veber"] for c in docked),
            "combined_pass_in_docked_set": sum(druglike[c]["combined"] for c in docked)},
        "machine_learning": dict(
            rows=len(ml),
            **{"predicted_" + k: v for k, v in
               Counter(v["prediction"] for v in ml.values()).items()},
            **{"ad_" + k: v for k, v in
               Counter(v["ad_status"] for v in ml.values()).items()}),
        "external_test_set": metrics,
        "consensus": consensus,
    }
    apds = {v["apd"] for v in ml.values()}
    report["machine_learning"]["apd_threshold"] = (
        next(iter(apds)) if len(apds) == 1 else sorted(apds))

    def section(title, mapping):
        print("\n" + title)
        print("-" * len(title))
        for k, v in mapping.items():
            if k == "tier_1_compounds":
                continue
            print("  {:<32} {}".format(k, "{:.4f}".format(v)
                                       if isinstance(v, float) else v))

    print("A2A-iCAP - verification of published screening numbers")
    print("data root: {}".format(args.data_root))
    section("GNINA docking", report["docking"])
    section("Drug-likeness (RDKit)", report["druglikeness"])
    section("ML prediction + applicability domain", report["machine_learning"])
    if metrics:
        section("External test set (held out)", metrics)
    section("Consensus tiers", consensus)

    if dock_stats["best_pose_mismatches"]:
        print("\nWARNING: {} ligand(s) where the recomputed best-CNN pose differs "
              "from the BestPose sheet.".format(dock_stats["best_pose_mismatches"]))
    else:
        print("\nBest-pose selection independently reproduced for all ligands.")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("JSON written to {}".format(args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
