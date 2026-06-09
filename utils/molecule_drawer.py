import io
import streamlit as st
from rdkit import Chem


def render_molecule_2d_bw(smiles, caption="2D Structure", width=420, height=300):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        st.warning("Invalid SMILES: cannot render 2D structure.")
        return

    # Try Cairo-based PNG drawing first
    try:
        from rdkit.Chem.Draw import rdMolDraw2D
        from PIL import Image

        mol_prep = rdMolDraw2D.PrepareMolForDrawing(mol)
        drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
        opts = drawer.drawOptions()
        opts.useBWAtomPalette()
        opts.addStereoAnnotation = False
        opts.addAtomIndices = False
        opts.addBondIndices = False
        opts.padding = 0.04
        opts.bondLineWidth = 2
        drawer.DrawMolecule(mol_prep)
        drawer.FinishDrawing()
        png_data = drawer.GetDrawingText()
        img = Image.open(io.BytesIO(png_data))
        st.image(img, caption=caption, use_container_width=False)
        return
    except Exception:
        pass

    # Fallback: SVG-based drawing (no Cairo needed)
    try:
        from rdkit.Chem.Draw import rdMolDraw2D

        mol_prep = rdMolDraw2D.PrepareMolForDrawing(mol)
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        opts = drawer.drawOptions()
        opts.useBWAtomPalette()
        opts.padding = 0.04
        opts.bondLineWidth = 2
        drawer.DrawMolecule(mol_prep)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
        st.markdown(
            f'<div style="text-align:center">{svg}</div>',
            unsafe_allow_html=True,
        )
        if caption:
            st.caption(caption)
        return
    except Exception:
        pass

    # Fallback: PIL-based drawing via rdkit.Chem.Draw
    try:
        from rdkit.Chem import Draw

        img = Draw.MolToImage(mol, size=(width, height))
        st.image(img, caption=caption, use_container_width=False)
        return
    except Exception:
        pass

    # Last resort: show SMILES as text
    st.caption(f"2D viewer unavailable  |  SMILES: `{smiles}`")
