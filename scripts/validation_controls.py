"""
Y-randomization control and baseline-model comparison for the A2A classifier.

Two gaps in the original validation are closed here:

1. **Y-randomization.** The KNIME workflow describes 30 shuffled-label trials but
   no control values were ever recorded. Without them, "the model learned real
   structure-activity signal" is an unsupported claim.

2. **Baseline comparison.** No simpler model was ever compared against the
   Random Forest, so the reported performance had nothing to be judged against.

Both reuse the exact feature matrices exported by KNIME (Train/Test set
prediction workbooks), so nothing is recomputed from SMILES and the split is the
published scaffold/activity-aware one.

    python scripts/validation_controls.py --data-root "<ML-Classification folder>" \
        --trials 30 --out docs/validation_controls.json

Every model, real and shuffled, uses the same Random Forest configuration as the
deployed artefact (500 trees, sqrt features) so the comparison is like-for-like.
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np

warnings.simplefilter("ignore")

TRAIN_FILE = "Train set prediction.xlsx"
TEST_FILE = "Test set prediction.xlsx"
LABEL_COLUMN = "activity"
POSITIVE = "Active"

RF_KWARGS = dict(n_estimators=500, max_features="sqrt", min_samples_leaf=1,
                 n_jobs=-1, random_state=34791)


def load_matrix(path: Path, feature_names=None):
    """Read a KNIME prediction workbook into (X, y, feature_names)."""
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook.worksheets[0]
    rows = worksheet.iter_rows(values_only=True)
    header = list(next(rows))
    data = [r for r in rows if any(v is not None for v in r)]
    workbook.close()

    if feature_names is None:
        # Exclude the label, prediction outputs and any non-numeric column.
        drop_prefixes = ("P (", "Prediction", "Domain", "APD")
        feature_names = [
            h for h in header
            if h and h != LABEL_COLUMN
            and not str(h).startswith(drop_prefixes)
            and "Smiles" not in str(h) and "RDKit" not in str(h)
        ]

    index = {h: i for i, h in enumerate(header)}
    missing = [f for f in feature_names if f not in index]
    if missing:
        raise SystemExit(f"{path.name}: {len(missing)} features missing, "
                         f"e.g. {missing[:5]}")

    label_i = index[LABEL_COLUMN]
    X = np.zeros((len(data), len(feature_names)), dtype=np.float32)
    y = np.zeros(len(data), dtype=np.int8)
    for r, row in enumerate(data):
        for c, name in enumerate(feature_names):
            v = row[index[name]]
            X[r, c] = 0.0 if v is None else float(v)
        y[r] = 1 if str(row[label_i]).strip() == POSITIVE else 0
    return X, y, feature_names


def scores(y_true, y_pred, y_prob=None):
    from sklearn.metrics import (balanced_accuracy_score, matthews_corrcoef,
                                 roc_auc_score)
    out = {
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
    }
    if y_prob is not None:
        out["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    return out


def fit_score(model, Xtr, ytr, Xte, yte):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    prob = (model.predict_proba(Xte)[:, 1]
            if hasattr(model, "predict_proba") else None)
    return scores(yte, pred, prob)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import BernoulliNB
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier

    print("loading KNIME feature matrices...")
    t0 = time.time()
    Xtr, ytr, names = load_matrix(args.data_root / TRAIN_FILE)
    Xte, yte, _ = load_matrix(args.data_root / TEST_FILE, names)
    print(f"  train {Xtr.shape}  test {Xte.shape}  features {len(names)}")
    print(f"  train Active {int(ytr.sum())}/{len(ytr)}  "
          f"test Active {int(yte.sum())}/{len(yte)}   ({time.time()-t0:.0f}s)")

    report = {"n_train": int(len(ytr)), "n_test": int(len(yte)),
              "n_features": len(names), "rf_config": {
                  k: v for k, v in RF_KWARGS.items() if k != "n_jobs"}}

    # ---------- Baselines ----------
    print("\n--- Baseline comparison (same split, same features) ---")
    baselines = {
        "Majority class": DummyClassifier(strategy="most_frequent"),
        "Decision tree (depth 5)": DecisionTreeClassifier(
            max_depth=5, random_state=34791),
        "Bernoulli naive Bayes": BernoulliNB(),
        "Logistic regression": make_pipeline(
            StandardScaler(with_mean=False),
            LogisticRegression(max_iter=2000, n_jobs=-1)),
        "Random Forest (this work)": RandomForestClassifier(**RF_KWARGS),
    }
    report["baselines"] = {}
    print(f"{'model':<28}{'BA':>8}{'MCC':>8}{'ROC-AUC':>10}")
    print("-" * 54)
    for label, model in baselines.items():
        t = time.time()
        m = fit_score(model, Xtr, ytr, Xte, yte)
        report["baselines"][label] = m
        print(f"{label:<28}{m['balanced_accuracy']:>8.3f}{m['mcc']:>8.3f}"
              f"{m.get('roc_auc', float('nan')):>10.3f}   ({time.time()-t:.0f}s)")

    real = report["baselines"]["Random Forest (this work)"]

    # ---------- Y-randomization ----------
    print(f"\n--- Y-randomization: {args.trials} shuffled-label trials ---")
    rng = np.random.default_rng(34791)
    trials = []
    for i in range(args.trials):
        y_shuffled = rng.permutation(ytr)
        m = fit_score(RandomForestClassifier(**RF_KWARGS), Xtr, y_shuffled,
                      Xte, yte)
        trials.append(m)
        if (i + 1) % 5 == 0 or i == 0:
            print(f"  trial {i+1:>2}/{args.trials}  BA={m['balanced_accuracy']:.3f}  "
                  f"AUC={m.get('roc_auc', float('nan')):.3f}")

    def summarise(key):
        vals = np.array([t[key] for t in trials if key in t])
        return {"mean": float(vals.mean()), "std": float(vals.std()),
                "min": float(vals.min()), "max": float(vals.max())}

    report["y_randomization"] = {
        "trials": args.trials,
        "balanced_accuracy": summarise("balanced_accuracy"),
        "roc_auc": summarise("roc_auc"),
        "mcc": summarise("mcc"),
        "real_model": real,
    }

    ba = report["y_randomization"]["balanced_accuracy"]
    auc = report["y_randomization"]["roc_auc"]
    print("\nresult")
    print(f"  real model         BA {real['balanced_accuracy']:.3f}   "
          f"AUC {real['roc_auc']:.3f}")
    print(f"  shuffled labels    BA {ba['mean']:.3f} +/- {ba['std']:.3f} "
          f"(max {ba['max']:.3f})   AUC {auc['mean']:.3f} +/- {auc['std']:.3f} "
          f"(max {auc['max']:.3f})")
    gap = real["balanced_accuracy"] - ba["max"]
    print(f"  margin over the best shuffled trial: {gap:+.3f} BA")
    verdict = ("PASS: the real model outperforms every shuffled-label trial, so "
               "the learned signal is not chance correlation."
               if gap > 0 else
               "FAIL: at least one shuffled-label model matched the real model.")
    print(f"  {verdict}")
    report["y_randomization"]["margin_over_best_shuffled_ba"] = float(gap)
    report["y_randomization"]["verdict"] = "pass" if gap > 0 else "fail"

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nJSON written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
