"""Regression tests for the 2D molecule renderer."""

import sys
import types
import unittest
from unittest.mock import patch


# The pure drawing helpers do not need a running Streamlit application.
streamlit_stub = types.ModuleType("streamlit")
streamlit_stub.warning = lambda *args, **kwargs: None
streamlit_stub.image = lambda *args, **kwargs: None
streamlit_stub.markdown = lambda *args, **kwargs: None
streamlit_stub.caption = lambda *args, **kwargs: None
sys.modules.setdefault("streamlit", streamlit_stub)

from rdkit import Chem

from utils import molecule_drawer
from utils.molecule_drawer import (
    _configure_draw_options,
    _prepare_molecule,
    molecule_to_svg,
)


CURCUMIN_ISOMERIC_SMILES = (
    "COC1=C(C=CC(=C1)/C=C/C(=O)CC(=O)/C=C/C2=CC(=C(C=C2)O)OC)O"
)


class MoleculeDrawerTests(unittest.TestCase):
    def test_curcumin_depiction_is_valid_svg(self):
        svg = molecule_to_svg(CURCUMIN_ISOMERIC_SMILES, width=280, height=220)

        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("bond-", svg)

    def test_preparation_preserves_curcumin_double_bond_stereo(self):
        expected = Chem.MolFromSmiles(CURCUMIN_ISOMERIC_SMILES)
        prepared = _prepare_molecule(CURCUMIN_ISOMERIC_SMILES)

        expected_stereo = [
            bond.GetStereo()
            for bond in expected.GetBonds()
            if bond.GetStereo() != Chem.BondStereo.STEREONONE
        ]
        prepared_stereo = [
            bond.GetStereo()
            for bond in prepared.GetBonds()
            if bond.GetStereo() != Chem.BondStereo.STEREONONE
        ]

        self.assertEqual(prepared_stereo, expected_stereo)
        self.assertEqual(prepared.GetNumConformers(), 1)
        self.assertFalse(prepared.GetConformer().Is3D())

    def test_invalid_smiles_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid SMILES"):
            _prepare_molecule("not-a-smiles")

    def test_publication_style_has_clear_bonds_and_labels(self):
        from rdkit.Chem.Draw import rdMolDraw2D

        options = rdMolDraw2D.MolDrawOptions()
        _configure_draw_options(options)

        self.assertAlmostEqual(options.bondLineWidth, 2.6)
        self.assertAlmostEqual(options.multipleBondOffset, 0.18)
        self.assertGreaterEqual(options.minFontSize, 13)
        self.assertFalse(options.scaleBondWidth)

    def test_streamlit_renderer_uses_local_svg_without_network(self):
        with (
            patch.object(molecule_drawer.st, "markdown") as markdown,
            patch.object(molecule_drawer.st, "caption") as caption,
            patch.object(
                molecule_drawer,
                "_render_pubchem_fallback",
                side_effect=AssertionError("network fallback should not be called"),
            ),
        ):
            molecule_drawer.render_molecule_2d(
                CURCUMIN_ISOMERIC_SMILES,
                caption="Curcumin",
                width=280,
                height=220,
            )

        rendered_html = markdown.call_args.args[0]
        self.assertIn("<svg", rendered_html)
        self.assertIn('aria-label="Curcumin"', rendered_html)
        caption.assert_called_once_with("Curcumin")


if __name__ == "__main__":
    unittest.main()
