from pathlib import Path
import shlex

import py3Dmol
import streamlit.components.v1 as components

from utils.vina_runner import get_shell_path, run_shell_command


def convert_pdbqt_to_pdb_with_obabel(input_pdbqt, output_pdb):
    input_pdbqt = Path(input_pdbqt)
    output_pdb = Path(output_pdb)

    if not input_pdbqt.exists():
        raise FileNotFoundError(f"Docked pose file not found: {input_pdbqt}")

    input_shell = get_shell_path(input_pdbqt)
    output_shell = get_shell_path(output_pdb)

    command = f"obabel {shlex.quote(input_shell)} -O {shlex.quote(output_shell)}"
    returncode, stdout, stderr = run_shell_command(command)

    if returncode != 0:
        raise RuntimeError(f"Ligand pose conversion failed.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    if not output_pdb.exists():
        raise RuntimeError("Converted ligand pose PDB file was not created.")

    return output_pdb


def render_docking_pose_3d(receptor_pdb_path="data/5IU4_final_aligned.pdb", ligand_pose_pdbqt_path=None, height=600):
    receptor_pdb_path = Path(receptor_pdb_path)

    if not receptor_pdb_path.exists():
        components.html("<p style='color:red;'>Receptor structure is not available.</p>", height=120)
        return

    if ligand_pose_pdbqt_path is None or str(ligand_pose_pdbqt_path).strip() == "":
        components.html("<p style='color:red;'>No docked ligand pose is available.</p>", height=120)
        return

    ligand_pose_pdbqt_path = Path(ligand_pose_pdbqt_path)

    if not ligand_pose_pdbqt_path.exists():
        components.html("<p style='color:red;'>Docked ligand pose file is not available.</p>", height=120)
        return

    ligand_pose_pdb_path = ligand_pose_pdbqt_path.with_suffix(".pdb")

    if not ligand_pose_pdb_path.exists():
        convert_pdbqt_to_pdb_with_obabel(input_pdbqt=ligand_pose_pdbqt_path, output_pdb=ligand_pose_pdb_path)

    receptor_text = receptor_pdb_path.read_text(errors="ignore")
    ligand_text = ligand_pose_pdb_path.read_text(errors="ignore")

    view = py3Dmol.view(width="100%", height=height)
    view.addModel(receptor_text, "pdb")
    view.setStyle({"model": 0}, {"cartoon": {"color": "skyblue", "opacity": 0.95, "thickness": 0.45}})
    view.addModel(ligand_text, "pdb")
    view.setStyle({"model": 1}, {"stick": {"colorscheme": "greenCarbon", "radius": 0.28}})
    view.zoomTo({"model": 1})
    view.zoom(0.75)
    view.setBackgroundColor("white")

    html = view._make_html()
    components.html(html, height=height + 20)
