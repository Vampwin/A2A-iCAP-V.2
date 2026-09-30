"""
Check that the app's featurisation reproduces the published screening result.

1024 of the model's 1096 input features are fingerprint bits, so if the app
computes a different fingerprint from the one the model was trained on, the
predictions are meaningless while still looking plausible. This script measures
that directly: it featurises the 630 published screening compounds with the
app's own code and compares the resulting predictions against the published
KNIME output.

    python scripts/verify_featurisation.py \
        --published "<path>/ML_Classification_Prediction_Results.xlsx"

Reference measurements (630 compounds, published: 470 Active / 160 Inactive):

    fingerprint                     agreement   predicted Active
    Morgan r=2, 1024 bits (wrong)       28.3%                 22
    RDKit path, 1024 bits (correct)     72.2%                441

Agreement does not reach 100% because models/final_model.pkl is a scikit-learn
re-export rather than a byte-exact copy of the KNIME Random Forest: fed KNIME's
own stored feature values it agrees with KNIME on 95.1% of the held-out test
set. 72% is therefore close to the achievable ceiling; ~28% is not.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Below this, the featurisation is definitely inconsistent with the model.
MIN_ACCEPTABLE_AGREEMENT = 0.60


def load_published(path: Path):
    import openpyxl

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook.worksheets[0]
    rows = worksheet.iter_rows(values_only=True)
    header = list(next(rows))
    records = [dict(zip(header, r, strict=False)) for r in rows
               if any(v is not None for v in r)]
    workbook.close()
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify app featurisation against the published screening run.")
    parser.add_argument(
        "--published", required=True, type=Path,
        help="path to ML_Classification_Prediction_Results.xlsx")
    parser.add_argument("--min-agreement", type=float,
                        default=MIN_ACCEPTABLE_AGREEMENT)
    args = parser.parse_args()

    if not args.published.exists():
        print(f"ERROR: published workbook not found: {args.published}")
        return 2

    import joblib

    from utils.ml_features import calculate_ml_features_from_smiles

    records = load_published(args.published)
    smiles = [str(r["SMILES"]) for r in records]
    published = np.array([str(r["Prediction (activity)"]).strip().lower()
                          for r in records])
    print(f"published compounds: {len(records)}")
    print(f"published classes  : {dict(Counter(published))}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = joblib.load(ROOT / "models" / "final_model.pkl")
        names = list(joblib.load(ROOT / "models" / "feature_names.pkl"))
        features, valid = calculate_ml_features_from_smiles(smiles, names)

    n_bits = sum(1 for n in names if str(n).startswith("bitvector"))
    print(f"features           : {len(names)} ({n_bits} fingerprint bits, "
          f"{len(names) - n_bits} descriptors)")
    print(f"unparsable SMILES  : {int((~valid).sum())}")

    active_index = list(model.classes_).index(1)
    probability = model.predict_proba(features)[:, active_index]
    predicted = np.where(probability >= 0.50, "active", "inactive")

    agreement = float((predicted == published).mean())
    n_active = int((predicted == "active").sum())
    n_published_active = int((published == "active").sum())

    print()
    print(f"app predicted Active : {n_active}")
    print(f"published Active     : {n_published_active}")
    print(f"class agreement      : {agreement * 100:.1f}%")

    if agreement < args.min_agreement:
        print()
        print(f"FAIL: agreement {agreement * 100:.1f}% is below the "
              f"{args.min_agreement * 100:.0f}% floor.")
        print("The app's featurisation does not match the model's training "
              "features. Check the fingerprint settings in utils/ml_features.py "
              "against the KNIME RDKit Fingerprint node (fp_type=rdkit, "
              "num_bits=1024, min_path=1, max_path=7).")
        return 1

    print()
    print(f"PASS: agreement {agreement * 100:.1f}% is consistent with the "
          "published screening run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
