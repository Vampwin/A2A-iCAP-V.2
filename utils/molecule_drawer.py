"""Validated, deterministic 2D molecular structure rendering.

RDKit is the primary renderer so the preview is generated from the same
parsed molecular graph used by the rest of the application. PubChem is kept
only as a network fallback when the local drawing backend is unavailable.
"""

from html import escape
from urllib.parse import quote
from urllib.request import urlopen

import streamlit as st
from rdkit import Chem


def _prepare_molecule(smiles: str):
    """Parse a SMILES string and generate fresh, canonical 2D coordinates."""
    cleaned_smiles = str(smiles).strip()
    if not cleaned_smiles:
        raise ValueError("SMILES is empty.")

    mol = Chem.MolFromSmiles(cleaned_smiles)
    if mol is None:
        raise ValueError("Invalid SMILES.")

    # Preserve any E/Z and tetrahedral stereochemistry supplied in the SMILES.
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)

    # Always replace inherited/remote coordinates. Canonical orientation makes
    # the same structure render consistently and avoids folded/overlapping bonds.
    from rdkit.Chem import rdDepictor

    rdDepictor.Compute2DCoords(mol, canonOrient=True, clearConfs=True)
    return mol


def _configure_draw_options(options) -> None:
    """Apply a clear, publication-style visual treatment."""
    options.addStereoAnnotation = True
    options.padding = 0.06
    options.bondLineWidth = 2.6
    # Keep the requested pixel width even when a large molecule is scaled down
    # to fit the card; otherwise long structures can end up with hairline bonds.
    options.scaleBondWidth = False
    options.multipleBondOffset = 0.18
    options.minFontSize = 13
    options.maxFontSize = 24
    options.annotationFontScale = 0.72


def _molecule_to_svg(mol, width: int, height: int) -> str:
    """Return an RDKit SVG depiction for a prepared molecule."""
    if width < 1 or height < 1:
        raise ValueError("Image dimensions must be positive.")

    from rdkit.Chem.Draw import rdMolDraw2D

    mol = rdMolDraw2D.PrepareMolForDrawing(mol, forceCoords=False)

    drawer = rdMolDraw2D.MolDraw2DSVG(int(width), int(height))
    options = drawer.drawOptions()
    _configure_draw_options(options)
    # RDKit's conventional element colours (for example oxygen in red and
    # nitrogen in blue) remain enabled to make heteroatoms easy to identify.

    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    if not svg or "<svg" not in svg:
        raise RuntimeError("RDKit did not produce a valid SVG depiction.")
    return svg


def molecule_to_svg(smiles: str, width: int = 420, height: int = 300) -> str:
    """Return an RDKit SVG depiction for a validated SMILES string."""
    return _molecule_to_svg(_prepare_molecule(smiles), width, height)


def _render_pubchem_fallback(mol, caption: str, width: int, height: int) -> bool:
    """Render a PubChem PNG from normalized isomeric SMILES as a fallback."""
    normalized_smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    encoded = quote(normalized_smiles, safe="")
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/"
        f"{encoded}/PNG?record_type=2d&image_size={width}x{height}"
    )

    try:
        with urlopen(url, timeout=8) as response:
            if response.status != 200:
                return False
            png_bytes = response.read()
        st.image(png_bytes, caption=caption, use_container_width=False)
        return True
    except Exception:
        return False


def render_molecule_2d(
    smiles: str,
    caption: str = "2D Structure",
    width: int = 420,
    height: int = 300,
):
    """Validate and render a clear 2D structure from a SMILES string."""
    try:
        mol = _prepare_molecule(smiles)
    except (TypeError, ValueError):
        st.warning("Invalid SMILES — cannot render 2D structure.")
        return

    try:
        svg = _molecule_to_svg(mol, width=width, height=height)
        accessible_label = escape(str(caption or "2D molecular structure"), quote=True)
        st.markdown(
            (
                '<div class="molecule-structure" role="img" '
                f'aria-label="{accessible_label}" style="display:flex;'
                'justify-content:center;align-items:center;background:#FFFFFF;'
                'border:1px solid #DDE8E7;border-radius:16px;padding:10px;'
                'box-shadow:0 4px 14px rgba(27,107,107,0.08);overflow:hidden">'
                f"{svg}</div>"
            ),
            unsafe_allow_html=True,
        )
        if caption:
            st.caption(caption)
        return
    except Exception:
        pass

    if _render_pubchem_fallback(mol, caption, width, height):
        return

    st.caption(f"2D viewer unavailable  |  SMILES: `{Chem.MolToSmiles(mol)}`")


def render_molecule_2d_bw(
    smiles: str,
    caption: str = "2D Structure",
    width: int = 420,
    height: int = 300,
):
    """Backward-compatible alias for older page imports."""
    return render_molecule_2d(smiles, caption=caption, width=width, height=height)
