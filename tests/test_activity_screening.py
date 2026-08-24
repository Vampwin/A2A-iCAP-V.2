"""Tests for natural-product-friendly activity screening bands."""

import unittest

from utils.activity_screening import (
    POSSIBLE_LABEL,
    PROMISING_LABEL,
    UNAVAILABLE_LABEL,
    WEAK_LABEL,
    classify_activity_signal,
    consensus_activity_points,
)


class ActivityScreeningTests(unittest.TestCase):
    def test_default_boundaries_create_three_evidence_bands(self):
        self.assertEqual(classify_activity_signal(0.50), PROMISING_LABEL)
        self.assertEqual(classify_activity_signal(0.49), POSSIBLE_LABEL)
        self.assertEqual(classify_activity_signal(0.40), POSSIBLE_LABEL)
        self.assertEqual(classify_activity_signal(0.39), WEAK_LABEL)

    def test_possible_signal_receives_partial_consensus_support(self):
        self.assertEqual(consensus_activity_points(PROMISING_LABEL), 2)
        self.assertEqual(consensus_activity_points(POSSIBLE_LABEL), 1)
        self.assertEqual(consensus_activity_points(WEAK_LABEL), 0)

    def test_missing_probability_is_unavailable(self):
        self.assertEqual(classify_activity_signal(float("nan")), UNAVAILABLE_LABEL)

    def test_invalid_threshold_order_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_activity_signal(0.50, promising_threshold=0.40, possible_threshold=0.50)


if __name__ == "__main__":
    unittest.main()
