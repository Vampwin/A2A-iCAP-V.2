import json
import platform
import re
import shlex
import subprocess
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem


def windows_path_to_wsl(path):
    path = Path(path).resolve()
    path_str = str(path)
    drive = path_str[0].lower()
    rest = path_str[2:].replace("\\", "/")
    return f"/mnt/{drive}{rest}"


def get_shell_path(path):
    if platform.system() == "Windows":
        return windows_path_to_wsl(path)
    return str(Path(path).resolve())


def run_shell_command(command):
    if platform.system() == "Windows":
        completed = subprocess.run(
            ["wsl", "bash", "-lc", command],
            capture_output=True,
            text=True
        )
    else:
        completed = subprocess.run(command, shell=True, capture_output=True, text=True)
    return completed.returncode, completed.stdout, completed.stderr


def run_wsl_command(command):
    return run_shell_command(command)


def load_vina_config(config_path="data/vina_config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_filename(text):
    text = str(text).strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    return text[:80]


def generate_3d_ligand_sdf(smiles, output_sdf):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        raise ValueError("Invalid SMILES — could not parse the molecular structure.")

    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    embed_status = AllChem.EmbedMolecule(mol, params)

    if embed_status != 0:
        raise ValueError("3D embedding failed.")

    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    except Exception:
        AllChem.UFFOptimizeMolecule(mol, maxIters=500)

    writer = Chem.SDWriter(str(output_sdf))
    writer.write(mol)
    writer.close()
    return output_sdf


def convert_sdf_to_pdbqt_with_obabel(input_sdf, output_pdbqt):
    input_shell = get_shell_path(input_sdf)
    output_shell = get_shell_path(output_pdbqt)
    command = (
        f"obabel {shlex.quote(input_shell)} "
        f"-O {shlex.quote(output_shell)} "
        f"--partialcharge gasteiger"
    )
    returncode, stdout, stderr = run_shell_command(command)
    if returncode != 0:
        raise RuntimeError(f"Ligand format conversion failed.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
    if not Path(output_pdbqt).exists():
        raise RuntimeError("Ligand PDBQT file was not created — check docking software configuration.")
    return output_pdbqt


def parse_vina_best_affinity(vina_stdout, log_path=None):
    text = vina_stdout or ""
    if log_path is not None and Path(log_path).exists():
        try:
            text += "\n" + Path(log_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    pattern = re.compile(r"^\s*1\s+(-?\d+\.\d+)", re.MULTILINE)
    match = pattern.search(text)
    if match:
        return float(match.group(1))
    return None


def assign_docking_evidence(vina_affinity):
    if vina_affinity is None:
        return "Failed"
    if vina_affinity <= -7.5:
        return "Strong"
    elif vina_affinity <= -6.5:
        return "Moderate"
    else:
        return "Weak"


def run_vina_docking_for_compound(compound_name, smiles, config_path="data/vina_config.json", output_root="outputs"):
    config = load_vina_config(config_path)
    compound_id = sanitize_filename(compound_name)

    ligand_dir = Path(output_root) / "ligands"
    docking_dir = Path(output_root) / "docking"
    pose_dir = Path(output_root) / "poses"

    ligand_dir.mkdir(parents=True, exist_ok=True)
    docking_dir.mkdir(parents=True, exist_ok=True)
    pose_dir.mkdir(parents=True, exist_ok=True)

    ligand_sdf = ligand_dir / f"{compound_id}.sdf"
    ligand_pdbqt = ligand_dir / f"{compound_id}.pdbqt"
    output_pose = pose_dir / f"{compound_id}_vina_out.pdbqt"
    log_file = docking_dir / f"{compound_id}_vina.log"

    generate_3d_ligand_sdf(smiles, ligand_sdf)
    convert_sdf_to_pdbqt_with_obabel(ligand_sdf, ligand_pdbqt)

    receptor_path = Path(config["receptor_pdbqt"]).resolve()
    if not receptor_path.exists():
        raise FileNotFoundError(f"Receptor PDBQT not found: {receptor_path}")

    receptor_wsl = get_shell_path(receptor_path)
    ligand_wsl = get_shell_path(ligand_pdbqt)
    output_pose_wsl = get_shell_path(output_pose)

    command = (
        f"vina "
        f"--receptor {shlex.quote(receptor_wsl)} "
        f"--ligand {shlex.quote(ligand_wsl)} "
        f"--center_x {float(config['center_x'])} "
        f"--center_y {float(config['center_y'])} "
        f"--center_z {float(config['center_z'])} "
        f"--size_x {float(config['size_x'])} "
        f"--size_y {float(config['size_y'])} "
        f"--size_z {float(config['size_z'])} "
        f"--exhaustiveness {int(config.get('exhaustiveness', 8))} "
        f"--num_modes {int(config.get('num_modes', 9))} "
        f"--energy_range {float(config.get('energy_range', 3))} "
        f"--cpu {int(config.get('cpu', 4))} "
        f"--out {shlex.quote(output_pose_wsl)}"
    )

    returncode, stdout, stderr = run_shell_command(command)

    log_text = f"COMMAND:\n{command}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n"
    Path(log_file).write_text(log_text, encoding="utf-8", errors="ignore")

    if returncode != 0:
        raise RuntimeError(f"Docking calculation failed.\nCommand:\n{command}\n\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    vina_affinity = parse_vina_best_affinity(vina_stdout=stdout, log_path=log_file)
    docking_evidence = assign_docking_evidence(vina_affinity)

    return {
        "compound_name": compound_name,
        "vina_affinity_kcal_mol": vina_affinity,
        "docking_evidence": docking_evidence,
        "docking_engine": "Molecular Docking",
        "ligand_sdf": str(ligand_sdf),
        "ligand_pdbqt": str(ligand_pdbqt),
        "output_pose_pdbqt": str(output_pose),
        "vina_log": str(log_file),
        "docking_note": "Local docking completed"
    }
