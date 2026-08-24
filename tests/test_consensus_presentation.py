"""Tests for investor-facing consensus labels and percentages."""

import unittest

from utils.consensus_presentation import format_activity_percentages, outcome_for_tier


class ConsensusPresentationTests(unittest.TestCase):
    def test_binary_probability_is_shown_as_active_and_inactive(self):
        self.assertEqual(format_activity_percentages(0.78), ("78%", "22%"))

    def test_missing_probability_is_not_presented_as_a_number(self):
        self.assertEqual(format_activity_percentages(float("nan")), ("N/A", "N/A"))

    def test_internal_tiers_have_plain_language_outcomes(self):
        self.assertEqual(outcome_for_tier("Tier 1"), "Advance to laboratory validation")
        self.assertEqual(outcome_for_tier("Tier 2"), "Review evidence or optimize")
        self.assertEqual(outcome_for_tier("Tier 3"), "Defer or redesign")


if __name__ == "__main__":
    unittest.main()
