"""Confidence normalization rule (decision 0014), as a pure domain rule.

The reused prompt returns a qualitative label (`high` | `medium` | `low`); the persisted column and
the API contract (SPEC 6.5) are numeric. This maps the label to a coarse score. The three scores
encode the label, not measured precision — they are not evidence about the incident.
"""

from __future__ import annotations

CONFIDENCE_SCORES: dict[str, float] = {"high": 0.9, "medium": 0.6, "low": 0.3}


def confidence_to_score(label: object) -> float | None:
    """Map a 'high'|'medium'|'low' label to a coarse score; passthrough numeric; else None."""
    if isinstance(label, bool):  # guard: bool is an int subclass
        return None
    if isinstance(label, (int, float)):
        return float(label)
    if isinstance(label, str):
        return CONFIDENCE_SCORES.get(label.strip().lower())
    return None
