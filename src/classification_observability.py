"""Structured confidence and evidence for existing category decisions.

Attempt_80_ClassificationConfidenceExplainability

This module is observational only. It does not choose or alter categories.
"""

from __future__ import annotations

from typing import Any, Iterable


_REASON_EVIDENCE = (
    ("existing_semantic_category", "ExistingCategory"),
    ("source_category=", "SourceCategory"),
    ("title_rule=", "TitleRule"),
    ("organizer_hint=", "OrganizerHint"),
    ("venue_hint=", "VenueHint"),
    ("context_rule=", "ContextRule"),
    ("venue_type=", "VenueType"),
    ("description_rule=", "DescriptionRule"),
    ("no_category_rule_matched", "NoMatch"),
)


def evidence_from_reason(reason: str | None) -> list[str]:
    text = str(reason or "")
    evidence = [label for marker, label in _REASON_EVIDENCE if marker in text]
    return evidence or ["Unknown"]


def confidence_band(confidence: float | int | None) -> str:
    value = _confidence(confidence)
    if value >= 0.90:
        return "high"
    if value >= 0.75:
        return "medium"
    if value > 0:
        return "low"
    return "none"


def attach_classification_observability(event: dict[str, Any]) -> dict[str, Any]:
    copied = dict(event)
    confidence = _confidence(copied.get("category_confidence"))
    copied["category_confidence"] = confidence
    copied["category_evidence"] = evidence_from_reason(copied.get("category_reason"))
    copied["category_confidence_band"] = confidence_band(confidence)
    copied["category_needs_review"] = bool(copied.get("category")) and confidence < 0.75
    return copied


def sort_for_category_review(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return classified events from riskiest to strongest, deterministically."""
    observed = [attach_classification_observability(event) for event in events]
    return sorted(
        observed,
        key=lambda event: (
            _confidence(event.get("category_confidence")),
            str(event.get("title") or "").casefold(),
            str(event.get("event_id") or event.get("url") or ""),
        ),
    )


def _confidence(value: Any) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return round(min(1.0, max(0.0, number)), 4)
