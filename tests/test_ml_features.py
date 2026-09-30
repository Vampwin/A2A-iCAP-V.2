"""
Guards on the featurisation contract between the app and the trained model.

1024 of the model's 1096 features are fingerprint bits. If the fingerprint type
changes, predictions silently become meaningless rather than failing, so the
fingerprint identity is asserted directly here.

The end-to-end check against the published screening run lives in
scripts/verify_featurisation.py, which needs the published workbook.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

rdkit = pytest.importorskip("rdkit")
from rdkit import Chem, DataStructs  # noqa: E402
from rdkit.Chem import rdFingerprintGenerator as rfg  # noqa: E402

from utils.ml_features import (  # noqa: E402
    FP_MAX_PATH,
    FP_MIN_PATH,
    FP_NBITS,
    calculate_descriptor_features,
    calculate_fingerprint_bitvector,
    calculate_ml_features_from_smiles,
)

CAFFEINE = "Cn1c(=O)c2c(ncn2C)n(C)c1=O"
ISTRADEFYLLINE = "CCn1c(=O)n(CC)c2[nH]c(/C=C/c3ccc(OC)c(OC)c3)nc2c1=O"


@pytest.fixture(scope="module")
def mol():
    return Chem.MolFromSmiles(CAFFEINE)


class TestFingerprintSettings:
    """These values come from the KNIME RDKit Fingerprint node that produced
    the model's training features (fp_type=rdkit, num_bits=1024, paths 1-7)."""

    def test_settings_match_the_knime_workflow(self):
        assert (FP_MIN_PATH, FP_MAX_PATH, FP_NBITS) == (1, 7, 1024)

    def test_bitvector_has_one_column_per_bit(self, mol):
        bits = calculate_fingerprint_bitvector(mol)
        assert len(bits) == FP_NBITS
        assert set(bits) == {f"bitvector{i}" for i in range(FP_NBITS)}

    def test_values_are_binary(self, mol):
        assert set(calculate_fingerprint_bitvector(mol).values()) <= {0, 1}

    def test_fingerprint_is_path_based_not_morgan(self, mol):
        """The actual regression this module exists to prevent."""
        produced = np.array([calculate_fingerprint_bitvector(mol)[f"bitvector{i}"]
                             for i in range(FP_NBITS)])

        expected = np.zeros(FP_NBITS, dtype=int)
        DataStructs.ConvertToNumpyArray(
            rfg.GetRDKitFPGenerator(minPath=FP_MIN_PATH, maxPath=FP_MAX_PATH,
                                    fpSize=FP_NBITS).GetFingerprint(mol),
            expected)

        morgan = np.zeros(FP_NBITS, dtype=int)
        DataStructs.ConvertToNumpyArray(
            rfg.GetMorganGenerator(radius=2, fpSize=FP_NBITS).GetFingerprint(mol),
            morgan)

        assert np.array_equal(produced, expected), "not the RDKit path fingerprint"
        assert not np.array_equal(produced, morgan), "still producing Morgan bits"

    def test_different_molecules_give_different_bits(self):
        a = calculate_fingerprint_bitvector(Chem.MolFromSmiles(CAFFEINE))
        b = calculate_fingerprint_bitvector(Chem.MolFromSmiles(ISTRADEFYLLINE))
        assert a != b

    def test_same_molecule_is_deterministic(self, mol):
        assert calculate_fingerprint_bitvector(mol) == calculate_fingerprint_bitvector(mol)


class TestDescriptors:
    def test_core_descriptors_are_present(self, mol):
        features = calculate_descriptor_features(mol)
        for name in ("SlogP", "TPSA", "NumHBD", "NumHBA", "NumRings"):
            assert name in features

    def test_caffeine_values_are_chemically_sane(self, mol):
        features = calculate_descriptor_features(mol)
        assert features["NumRings"] == 2          # fused purine system
        assert features["NumHBD"] == 0            # no donors
        assert 55 < features["TPSA"] < 70         # literature TPSA ~61.8
        assert -2 < features["SlogP"] < 1         # literature logP ~-0.07


class TestFeatureMatrix:
    def test_matrix_is_aligned_to_requested_feature_names(self):
        names = ["SlogP", "TPSA", "bitvector0", "bitvector1"]
        frame, valid = calculate_ml_features_from_smiles([CAFFEINE], names)
        assert list(frame.columns) == names
        assert bool(valid.iloc[0])

    def test_unknown_feature_names_become_zero_not_an_error(self):
        frame, _ = calculate_ml_features_from_smiles(
            [CAFFEINE], ["SlogP", "NotARealDescriptor"])
        assert frame["NotARealDescriptor"].iloc[0] == 0

    def test_invalid_smiles_is_flagged_and_zero_filled(self):
        frame, valid = calculate_ml_features_from_smiles(
            ["not_a_molecule"], ["SlogP", "TPSA"])
        assert not bool(valid.iloc[0])
        assert (frame.iloc[0] == 0).all()

    def test_mixed_valid_and_invalid_keeps_row_order(self):
        frame, valid = calculate_ml_features_from_smiles(
            [CAFFEINE, "@@bad@@", ISTRADEFYLLINE], ["SlogP", "TPSA"])
        assert list(valid) == [True, False, True]
        assert len(frame) == 3

    def test_all_values_are_numeric(self):
        frame, _ = calculate_ml_features_from_smiles(
            [CAFFEINE], ["SlogP", "TPSA", "bitvector0"])
        assert frame.dtypes.apply(lambda d: np.issubdtype(d, np.number)).all()


class TestModelContract:
    """The saved feature list is the contract; a width mismatch means the model
    is being fed a differently-shaped matrix than it was trained on."""

    def test_feature_list_matches_model_input_width(self):
        joblib = pytest.importorskip("joblib")
        model_path = ROOT / "models" / "final_model.pkl"
        names_path = ROOT / "models" / "feature_names.pkl"
        if not model_path.exists() or not names_path.exists():
            pytest.skip("model artefacts not available in this checkout")

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = joblib.load(model_path)
            names = list(joblib.load(names_path))

        assert len(names) == model.n_features_in_ == 1096
        assert sum(1 for n in names if str(n).startswith("bitvector")) == FP_NBITS
