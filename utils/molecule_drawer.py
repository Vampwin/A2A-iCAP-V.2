from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D
from PIL import Image
import io
import streamlit as st


def render_molecule_2d_bw(smiles, caption="2D Structure", width=420, height=300):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        st.warning("Invalid SMILES: cannot render 2D structure.")
        return

    mol = rdMolDraw2D.PrepareMolForDrawing(mol)
    drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
    opts = drawer.drawOptions()
    opts.useBWAtomPalette()
    opts.addStereoAnnotation = False
    opts.addAtomIndices = False
    opts.addBondIndices = False
    opts.padding = 0.04
    opts.bondLineWidth = 2

    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()

    png_data = drawer.GetDrawingText()
    img = Image.open(io.BytesIO(png_data))
    st.image(img, caption=caption, use_container_width=False)
