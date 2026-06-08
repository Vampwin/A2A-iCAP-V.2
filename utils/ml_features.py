import numpy as np
import pandas as pd

from rdkit import Chem, DataStructs
from rdkit.Chem import Crippen, Lipinski, rdMolDescriptors
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator


MORGAN_RADIUS = 2
MORGAN_NBITS = 1024


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


def calculate_morgan_bitvector(mol, radius=MORGAN_RADIUS, n_bits=MORGAN_NBITS):
    features = {}
    generator = GetMorganGenerator(radius=radius, fpSize=n_bits)
    fp = generator.GetFingerprint(mol)
    arr = np.zeros((n_bits,), dtype=int)
    DataStructs.ConvertToNumpyArray(fp, arr)
    for i in range(n_bits):
        features[f"bitvector{i}"] = int(arr[i])
    return features


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
        fingerprint_features = calculate_morgan_bitvector(mol)

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
