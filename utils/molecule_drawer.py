"""
Molecule 2D structure renderer.
Primary method: PubChem Image API (no rdkit.Draw required — works on Streamlit Cloud).
Fallback: rdkit Cairo / SVG / PIL if available (works locally).
"""
import io
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import URLError

import streamlit as st
from rdkit import Chem


def render_molecule_2d_bw(smiles: str, caption: str = "2D Structure",
                           width: int = 420, height: int = 300):
    """Render a 2D molecular structure image from a SMILES string."""
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        st.warning("Invalid SMILES — cannot render 2D structure.")
        return

    # ── Method 1: PubChem REST API (no rdkit drawing required) ──────────────
    try:
        encoded = quote(smiles, safe="")
        url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/"
            f"{encoded}/PNG?record_type=2d&image_size={width}x{height}"
        )
        with urlopen(url, timeout=8) as resp:
            if resp.status == 200:
                png_bytes = resp.read()
                st.image(png_bytes, caption=caption, use_container_width=False)
                return
    except Exception:
        pass

    # ── Method 2: rdkit Cairo (works locally if cairo installed) ────────────
    try:
        from rdkit.Chem.Draw import rdMolDraw2D
        from PIL import Image

        mol_prep = rdMolDraw2D.PrepareMolForDrawing(mol)
        drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
        opts = drawer.drawOptions()
        opts.useBWAtomPalette()
        opts.addStereoAnnotation = False
        opts.padding = 0.04
        opts.bondLineWidth = 2
        drawer.DrawMolecule(mol_prep)
        drawer.FinishDrawing()
        img = Image.open(io.BytesIO(drawer.GetDrawingText()))
        st.image(img, caption=caption, use_container_width=False)
        return
    except Exception:
        pass

    # ── Method 3: rdkit SVG ──────────────────────────────────────────────────
    try:
        from rdkit.Chem.Draw import rdMolDraw2D

        mol_prep = rdMolDraw2D.PrepareMolForDrawing(mol)
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        drawer.drawOptions().useBWAtomPalette()
        drawer.DrawMolecule(mol_prep)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
        st.markdown(f'<div style="text-align:center">{svg}</div>',
                    unsafe_allow_html=True)
        if caption:
            st.caption(caption)
        return
    except Exception:
        pass

    # ── Method 4: rdkit PIL ──────────────────────────────────────────────────
    try:
        from rdkit.Chem import Draw
        img = Draw.MolToImage(mol, size=(width, height))
        st.image(img, caption=caption, use_container_width=False)
        return
    except Exception:
        pass

    # ── Last resort: show SMILES text ────────────────────────────────────────
    st.caption(f"2D viewer unavailable  |  SMILES: `{smiles}`")
