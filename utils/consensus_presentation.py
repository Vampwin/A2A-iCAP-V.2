"""Plain-language presentation helpers for the consensus results."""

import math


OUTCOME_BY_TIER = {
    "Tier 1": "Advance to laboratory validation",
    "Tier 2": "Scientific review required",
    "Tier 3": "Defer or redesign",
}


def outcome_for_tier(tier: str) -> str:
    """Translate an internal tier into an immediate next-step decision."""
    return OUTCOME_BY_TIER.get(str(tier), "Not yet ranked")


def format_activity_percentages(active_probability):
    """Return complementary Active/Inactive percentages for a binary model."""
    try:
        probability = float(active_probability)
    except (TypeError, ValueError):
        return "N/A", "N/A"

    if not math.isfinite(probability):
        return "N/A", "N/A"

    active_percent = max(0.0, min(100.0, probability * 100))
    return f"{active_percent:.0f}%", f"{100 - active_percent:.0f}%"


def activity_signal_tone(active_probability) -> str:
    """Map activity probability to goal-aligned UI color semantics."""
    try:
        probability = float(active_probability)
    except (TypeError, ValueError):
        return "neutral"

    if not math.isfinite(probability):
        return "neutral"
    if probability >= 0.65:
        return "good"
    if probability >= 0.35:
        return "warn"
    return "bad"


def outcome_tone(tier: str) -> str:
    """Return visual tone for an actionable shortlist outcome."""
    return {"Tier 1": "good", "Tier 2": "warn", "Tier 3": "bad"}.get(str(tier), "neutral")
