"""Regression test for the explicit Streamlit navigation labels."""

import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class NavigationTests(unittest.TestCase):
    def test_home_and_plain_language_page_labels_are_declared(self):
        declared_pages = []
        navigation_ran = []

        streamlit_stub = types.ModuleType("streamlit")

        def page(path, **kwargs):
            declared_pages.append((path, kwargs))
            return (path, kwargs)

        class Navigation:
            def run(self):
                navigation_ran.append(True)

        streamlit_stub.Page = page
        streamlit_stub.navigation = lambda pages, position: Navigation()
        streamlit_stub.set_page_config = lambda **kwargs: None

        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch.dict(sys.modules, {"streamlit": streamlit_stub}):
            runpy.run_path(str(app_path), run_name="__navigation_test__")

        labels = [options["title"] for _, options in declared_pages]
        self.assertEqual(labels[0], "Home")
        self.assertIn("Candidate Shortlist", labels)
        self.assertEqual(navigation_ran, [True])


if __name__ == "__main__":
    unittest.main()
