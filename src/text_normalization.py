"""Conservative text repair for common UTF-8 mojibake.

Attempt_25_Encoding_Normalization

Only strings containing strong mojibake markers are considered for repair.
A candidate replacement is accepted only when it reduces the marker score,
which keeps already-correct Unicode text unchanged.
"""

from __future__ import annotations

from typing import Any


MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â€",
    "â€“",
    "â€”",
    "â€™",
    "â€œ",
    "â€",
    "â€¦",
    "ðŸ",
    "ï¿½",
    "�",
)


def normalize_text(value: str) -> str:
    """Repair common UTF-8 decoded-as-Windows-1252 text when clearly safer."""
    original_score = mojibake_score(value)
    if original_score == 0:
        return value

    best = value
    best_score = original_score

    for encoding in ("cp1252", "latin1"):
        try:
            candidate = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

        candidate_score = mojibake_score(candidate)
        if candidate_score < best_score:
            best = candidate
            best_score = candidate_score

    return best


def normalize_value(value: Any) -> Any:
    """Recursively normalize strings while preserving container shape."""
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_value(item) for item in value)
    if isinstance(value, dict):
        return {key: normalize_value(item) for key, item in value.items()}
    return value


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized copy of one canonical event dictionary."""
    return {key: normalize_value(value) for key, value in event.items()}


def mojibake_score(value: str) -> int:
    """Return a weighted count of strong mojibake indicators."""
    return sum(value.count(marker) for marker in MOJIBAKE_MARKERS)
