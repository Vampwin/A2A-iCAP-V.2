# A₂A-iCAP

**An AI-Integrated Consensus Platform for Prioritising Natural Product-Like Adenosine A₂A Receptor Antagonist Candidates**

Submitted to the 2026 iBEC International Bioinformatics Engineering Competition
· Team **iCAP** (`IBEC26-37`) · Track: AI-driven life science discoveries

---

## What this is

Most virtual screening ranks compounds on a single score, and a single score is
easy to fool. Docking finds geometrically plausible poses for molecules that
never bind. A ligand-based model confidently scores molecules that lie far
outside the chemistry it was trained on — which is exactly the situation when
you point a model trained on synthetic xanthines at a natural product library.

A₂A-iCAP requires **four independent lines of evidence to agree** before a
compound is promoted, and exposes that reasoning in a web application rather
than burying it in a notebook.

| Evidence stream | Method | Pass criterion |
|---|---|---|
| Structure-based | GNINA docking, CNN-rescored, on A₂A receptor `5IU4` | CNN pose ≥ 0.65 **and** affinity ≤ −7.4 kcal/mol |
| Ligand-based | Random Forest on ChEMBL `CHEMBL251` Kᵢ data | predicted Active, confidence ≥ 0.70 |
| Prediction reliability | Fingerprint applicability domain | inside the domain (`Domain ≤ APD`) |
| Developability | RDKit properties, Lipinski-like + Veber-like | passes both filters |

All four → **Tier 1**. Reliability relaxed → **Tier 2**. Docking and
developability only → **Tier 3** (exploratory).

## Results

Screening the MedChemExpress Natural Product-Like Library (719 compounds → 678
prepared structures → 5,424 docked poses):

| Outcome | Count |
|---|---|
| Passed docking criteria | 231 / 678 |
| **Tier 1 — strict consensus** | **35** |
| Tier 2 — relaxed applicability domain | 21 |
| Tier 3 — docking + developability | 129 |
| Combined prioritised set | 185 |

Classifier on the **held-out, scaffold-aware external test set** (n = 939):
balanced accuracy **0.893**, ROC-AUC **0.953**, MCC **0.784**, F1 **0.900**.

Docking protocol validated by redocking the co-crystallised antagonist ZMA: the
22.5 Å box reproduced the crystallographic pose at **RMSD 1.08 Å**, while the
15 Å box (3.18 Å) and 30 Å box (2.86 Å) both failed the 2 Å criterion — note
that the 15 Å box scored *highest* by CNN, which is why RMSD rather than CNN
score decided the protocol.

**Controls.** Over 30 Y-randomisation trials, shuffled-label models sit at
chance (BA 0.495 ± 0.026) while the real model reaches 0.918 on the same
features — a margin of +0.360 BA over the best shuffled trial. Against
informative baselines on the identical split, the Random Forest leads the
strongest simple model (Bernoulli naive Bayes, BA 0.837) by 0.081 BA.

Every number above is regenerated from raw data by the scripts below.

## Reproducing the reported numbers

```bash
pip install openpyxl scikit-learn numpy

# Consensus tiers, docking counts, developability counts, external test metrics
python scripts/verify_consensus.py --data-root "<Poster Preparation Material>"

# Y-randomisation (30 trials) and the baseline model comparison
python scripts/validation_controls.py --data-root "<ML-Classification folder>" --trials 30

# Does the app's featurisation reproduce the published screening run?
python scripts/verify_featurisation.py --published "<ML_Classification_Prediction_Results.xlsx>"
```

`verify_consensus.py` reads only primary sources and deliberately **re-derives
the best pose per ligand from all 5,424 poses** instead of trusting the
pre-computed `BestPose` sheet. Current status: 0 mismatches across 678 ligands.

The source workbooks are not redistributed here — see
[Data and licensing](#data-and-licensing).

## Running the application

Deployed on Streamlit Cloud. To run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Docking additionally needs AutoDock Vina and Open Babel on `PATH`
(`packages.txt` installs them on Streamlit Cloud; on Windows the runner falls
back to WSL). ML prediction and developability work without them.

> **scikit-learn is pinned to 1.8.0 on purpose.** `models/final_model.pkl` was
> serialised with that version. An unpinned install silently unpickles the model
> under an unsupported version and keeps serving predictions, so the pin is a
> correctness requirement, not housekeeping.

## Layout

```text
app.py                     entry point and navigation
pages/                     five-step workflow, account settings
utils/
  ml_features.py           SMILES → 72 descriptors + 1024 path-fingerprint bits
  ad_assessment.py         applicability-domain scoring
  vina_runner.py           docking orchestration (native or WSL)
  activity_screening.py    activity bands
  consensus_presentation.py plain-language result mapping
models/                    trained model, feature list, AD reference, thresholds
data/                      prepared 5IU4 receptor and docking box configuration
scripts/                   verification and control experiments
tests/                     31 automated tests
```

## Development

```bash
pytest          # 31 tests
```

Tests cover consensus rules and their boundary conditions, featurisation
identity, descriptor sanity, feature-matrix alignment, invalid-input handling
and the model-input contract.

**Why the featurisation is tested by identity.** 1,024 of the model's 1,096
features are fingerprint bits, so the featurisation code and the trained model
form a contract. When it was broken — a Morgan fingerprint where the model
expected an RDKit path fingerprint — the application kept returning confident,
plausible-looking predictions while agreeing with the published screening run on
only 28% of compounds. Restoring the correct fingerprint raised that to 72%.
`tests/test_ml_features.py` now asserts the bits are the path fingerprint and
are *not* Morgan bits.

## Known limitations

1. **The deployed app does not reproduce the published protocol exactly.** It
   uses AutoDock Vina rather than GNINA and so cannot compute a CNN pose score;
   its applicability domain is a descriptor bounding-box check rather than the
   fingerprint-similarity method used for the published results; and its
   consensus page ranks by a weighted score rather than the published rule set.
   Tiers shown in the app are indicative and are **not** the published tiers.
2. **The deployed model is a scikit-learn re-export**, not a byte-exact copy of
   the KNIME Random Forest. Given KNIME's own feature values it agrees with the
   original on 95.1% of the held-out test set.
3. **No experimental validation.** Every output is a computational
   prioritisation hypothesis. Tier 1 compounds require radioligand binding and
   functional cAMP-based antagonism assays before being called antagonists.
4. **No retrospective enrichment benchmark.** Redocking validates the binding
   site definition, not the ability of the scoring function to rank actives
   above inactives. This is the most valuable addition still outstanding.
5. **Ambiguous-potency compounds (5 < pKᵢ < 6) were excluded** from training and
   evaluation, so the reported metrics do not describe the borderline region.
6. Rigid receptor, no explicit structural waters, single unionised protomer per
   ligand.

## Data and licensing

| Resource | Use | Terms |
|---|---|---|
| ChEMBL (`CHEMBL251`) | Training data — A₂A Kᵢ values | CC BY-SA 3.0 |
| PDB `5IU4` | Receptor structure (ZMA-bound A₂A) | Unrestricted |
| MCE Natural Product-Like Library | Screening library | **Commercial — not redistributed** |
| RDKit | Descriptors, fingerprints, depiction | BSD-3-Clause |
| GNINA | CNN-rescored docking (published results) | Apache-2.0 |
| AutoDock Vina | Docking in the application | Apache-2.0 |
| Open Babel | Format conversion | GPL-2.0 |
| KNIME | Model development workflow | GPL-3.0 |

Project code is MIT (see `LICENSE`). The curated ChEMBL training table and the
model derived from it inherit **CC BY-SA 3.0**. The MCE library is a commercial
catalogue: computed results keyed to catalogue identifiers are ours and are
shared, but the library structures are not redistributed — obtain them from the
vendor to repeat the screen. Open Babel is GPL-2.0 and is invoked as a separate
process rather than linked, so its copyleft does not extend to this source; any
container distributing the binary carries the corresponding notice.

## Scientific disclaimer

This is a research prioritisation tool, not a clinical decision aid. Predicted
activity, docking affinity, applicability domain and consensus tier are
computational evidence, not experimental confirmation.

## Acknowledgements

Faculty of Pharmaceutical Sciences and the Center of Excellence in Natural
Products for Ageing and Chronic Diseases, Chulalongkorn University. The authors
thank AI Longevity Co., Ltd. for support.
