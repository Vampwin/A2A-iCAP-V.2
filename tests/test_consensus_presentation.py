"""Tests for investor-facing consensus labels and percentages."""

import unittest

from utils.consensus_presentation import (
    activity_signal_tone,
    format_activity_percentages,
    outcome_for_tier,
    outcome_tone,
)


class ConsensusPresentationTests(unittest.TestCase):
    def test_binary_probability_is_shown_as_active_and_inactive(self):
        self.assertEqual(format_activity_percentages(0.78), ("78%", "22%"))

    def test_missing_probability_is_not_presented_as_a_number(self):
        self.assertEqual(format_activity_percentages(float("nan")), ("N/A", "N/A"))

    def test_internal_tiers_have_plain_language_outcomes(self):
        self.assertEqual(outcome_for_tier("Tier 1"), "Advance to laboratory validation")
        self.assertEqual(outcome_for_tier("Tier 2"), "Scientific review required")
        self.assertEqual(outcome_for_tier("Tier 3"), "Defer or redesign")

    def test_activity_colors_follow_the_screening_goal(self):
        self.assertEqual(activity_signal_tone(0.80), "good")
        self.assertEqual(activity_signal_tone(0.50), "warn")
        self.assertEqual(activity_signal_tone(0.21), "bad")

    def test_defer_is_not_presented_as_a_positive_outcome(self):
        self.assertEqual(outcome_tone("Tier 1"), "good")
        self.assertEqual(outcome_tone("Tier 2"), "warn")
        self.assertEqual(outcome_tone("Tier 3"), "bad")


if __name__ == "__main__":
    unittest.main()
