import numpy as np
import pandas as pd

from rdkit import Chem, DataStructs
from rdkit.Chem import Crippen, Lipinski, rdMolDescriptors
from rdkit.Chem.rdFingerprintGenerator import GetRDKitFPGenerator


# --- Fingerprint settings -------------------------------------------------
# These MUST match the fingerprint the model was trained on. The KNIME
# workflow that produced models/final_model.pkl used the RDKit Fingerprint
# node with fp_type = "rdkit" (the path-based fingerprint), num_bits = 1024,
# min_path = 1, max_path = 7, use_chirality = false.
#
# This module previously used a Morgan/ECFP fingerprint. Morgan and path-based
# fingerprints hash entirely different substructures into the 1024 bits that
# make up 1024 of the model's 1096 input features, so the model was being fed
# features unrelated to the ones it learned from. Measured against the 630
# published screening predictions:
#
#   Morgan r=2, 1024 bits   ->  28.3% class agreement,  22 predicted Active
#   RDKit path, 1024 bits   ->  72.2% class agreement, 441 predicted Active
#                               (published reference:  470 predicted Active)
#
# Do not change these values without re-running
# scripts/verify_featurisation.py, which is the regression guard.
FP_MIN_PATH = 1
FP_MAX_PATH = 7
FP_NBITS = 1024
FP_USE_CHIRALITY = False


def safe_value(func, mol, default=0.0):
    try:
        value = func(mol)
        if value is None:
            return default
        return value
    except Exception:
        return default


def calculate_descriptor_features(mol):
    features = {}

    features["SlogP"] = safe_value(Crippen.MolLogP, mol)
    features["TPSA"] = safe_value(rdMolDescriptors.CalcTPSA, mol)
    features["NumHBD"] = safe_value(Lipinski.NumHDonors, mol)
    features["NumHBA"] = safe_value(Lipinski.NumHAcceptors, mol)
    features["NumAmideBonds"] = safe_value(rdMolDescriptors.CalcNumAmideBonds, mol)
    features["NumHeteroAtoms"] = safe_value(rdMolDescriptors.CalcNumHeteroatoms, mol)
    features["NumStereocenters"] = safe_value(rdMolDescriptors.CalcNumAtomStereoCenters, mol)
    features["NumUnspecifiedStereocenters"] = safe_value(rdMolDescriptors.CalcNumUnspecifiedAtomStereoCenters, mol)
    features["NumRings"] = safe_value(rdMolDescriptors.CalcNumRings, mol)
    features["NumAromaticRings"] = safe_value(rdMolDescriptors.CalcNumAromaticRings, mol)
    features["NumSaturatedRings"] = safe_value(rdMolDescriptors.CalcNumSaturatedRings, mol)
    features["NumAliphaticRings"] = safe_value(rdMolDescriptors.CalcNumAliphaticRings, mol)
    features["NumAromaticHeterocycles"] = safe_value(rdMolDescriptors.CalcNumAromaticHeterocycles, mol)
    features["NumSaturatedHeterocycles"] = safe_value(rdMolDescriptors.CalcNumSaturatedHeterocycles, mol)
    features["NumAliphaticHeterocycles"] = safe_value(rdMolDescriptors.CalcNumAliphaticHeterocycles, mol)
    features["NumAromaticCarbocycles"] = safe_value(rdMolDescriptors.CalcNumAromaticCarbocycles, mol)
    features["NumAliphaticCarbocycles"] = safe_value(rdMolDescriptors.CalcNumAliphaticCarbocycles, mol)
    features["HallKierAlpha"] = safe_value(rdMolDescriptors.CalcHallKierAlpha, mol)
    features["kappa3"] = safe_value(rdMolDescriptors.CalcKappa3, mol)

    try:
        slogp_vsa = rdMolDescriptors.SlogP_VSA_(mol)
        for i, value in enumerate(slogp_vsa, start=1):
            features[f"slogp_VSA{i}"] = value
    except Exception:
        pass

    try:
        smr_vsa = rdMolDescriptors.SMR_VSA_(mol)
        for i, value in enumerate(smr_vsa, start=1):
            features[f"smr_VSA{i}"] = value
    except Exception:
        pass

    try:
        peoe_vsa = rdMolDescriptors.PEOE_VSA_(mol)
        for i, value in enumerate(peoe_vsa, start=1):
            features[f"peoe_VSA{i}"] = value
    except Exception:
        pass

    try:
        mqn_values = rdMolDescriptors.MQNs_(mol)
        for i, value in enumerate(mqn_values, start=1):
            features[f"MQN{i}"] = value
    except Exception:
        pass

    return features


def calculate_fingerprint_bitvector(mol, min_path=FP_MIN_PATH, max_path=FP_MAX_PATH,
                                    n_bits=FP_NBITS):
    """Path-based RDKit fingerprint matching the model's training features.

    Produces columns bitvector0 .. bitvector1023, the same naming the KNIME
    Expand Bit Vector node produced when the model was trained.
    """
    features = {}
    generator = GetRDKitFPGenerator(
        minPath=min_path,
        maxPath=max_path,
        fpSize=n_bits,
    )
    fp = generator.GetFingerprint(mol)
    arr = np.zeros((n_bits,), dtype=int)
    DataStructs.ConvertToNumpyArray(fp, arr)
    for i in range(n_bits):
        features[f"bitvector{i}"] = int(arr[i])
    return features


# Kept so that any external caller importing the old name keeps working; it now
# returns the correct path-based fingerprint, not a Morgan fingerprint.
calculate_morgan_bitvector = calculate_fingerprint_bitvector


def calculate_ml_features_from_smiles(smiles_list, feature_names):
    rows = []

    for smiles in smiles_list:
        mol = Chem.MolFromSmiles(str(smiles))

        if mol is None:
            row = {feature: 0 for feature in feature_names}
            row["_valid_smiles"] = False
            rows.append(row)
            continue

        descriptor_features = calculate_descriptor_features(mol)
        fingerprint_features = calculate_fingerprint_bitvector(mol)

        combined_features = {}
        combined_features.update(descriptor_features)
        combined_features.update(fingerprint_features)

        row = {feature: combined_features.get(feature, 0) for feature in feature_names}
        row["_valid_smiles"] = True
        rows.append(row)

    feature_df = pd.DataFrame(rows)
    valid_smiles = feature_df["_valid_smiles"].copy()
    feature_df = feature_df.drop(columns=["_valid_smiles"])
    feature_df = feature_df.apply(pd.to_numeric, errors="coerce").fillna(0)

    return feature_df, valid_smiles
