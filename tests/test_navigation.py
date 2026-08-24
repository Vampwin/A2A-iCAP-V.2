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
        navigation_sections = []

        streamlit_stub = types.ModuleType("streamlit")

        def page(path, **kwargs):
            declared_pages.append((path, kwargs))
            return (path, kwargs)

        class Navigation:
            def run(self):
                navigation_ran.append(True)

        streamlit_stub.Page = page
        def navigation(pages, position):
            navigation_sections.extend(pages.keys())
            return Navigation()

        streamlit_stub.navigation = navigation
        streamlit_stub.set_page_config = lambda **kwargs: None

        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch.dict(sys.modules, {"streamlit": streamlit_stub}):
            runpy.run_path(str(app_path), run_name="__navigation_test__")

        labels = [options["title"] for _, options in declared_pages]
        self.assertEqual(labels[0], "Home")
        self.assertIn("5. Candidate Shortlist", labels)
        self.assertEqual(navigation_sections, ["Overview", "Screening workflow", "Account"])
        self.assertEqual(navigation_ran, [True])

    def test_home_is_a_public_overview(self):
        home_path = Path(__file__).resolve().parents[1] / "pages" / "0_Home.py"
        source = home_path.read_text(encoding="utf-8")
        self.assertIn("get_auth_state()", source)
        self.assertNotIn("require_login()", source)

    def test_auth_back_link_stays_visible_when_scroll_position_is_retained(self):
        auth_path = Path(__file__).resolve().parents[1] / "utils" / "auth.py"
        source = auth_path.read_text(encoding="utf-8")
        self.assertIn('label="Back to public overview"', source)
        self.assertIn("position: fixed", source)
        self.assertIn("top: calc(4.5rem", source)


if __name__ == "__main__":
    unittest.main()
