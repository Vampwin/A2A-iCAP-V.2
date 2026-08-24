"""Evidence-based activity screening bands for early candidate triage."""

import math


PROMISING_LABEL = "Predicted Active"
POSSIBLE_LABEL = "Possible Activity"
WEAK_LABEL = "Predicted Inactive"
UNAVAILABLE_LABEL = "Unavailable"


def classify_activity_signal(
    probability,
    promising_threshold: float = 0.50,
    possible_threshold: float = 0.40,
) -> str:
    """Classify a model score without treating borderline evidence as inactivity."""
    if possible_threshold > promising_threshold:
        raise ValueError("possible_threshold must not exceed promising_threshold")

    try:
        value = float(probability)
    except (TypeError, ValueError):
        return UNAVAILABLE_LABEL

    if not math.isfinite(value):
        return UNAVAILABLE_LABEL
    if value >= promising_threshold:
        return PROMISING_LABEL
    if value >= possible_threshold:
        return POSSIBLE_LABEL
    return WEAK_LABEL


def consensus_activity_points(label: str) -> int:
    """Return conservative consensus points for the three activity bands."""
    return {
        PROMISING_LABEL: 2,
        POSSIBLE_LABEL: 1,
        WEAK_LABEL: 0,
    }.get(str(label), 0)
