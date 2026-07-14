"""Deterministic event completeness scoring.

Attempt_57_EventCompletenessIntelligence

Completeness measures whether useful publication and review fields are present. It does
not determine event identity or override source provenance; duplicate resolution may use
it to choose the most informative canonical record, with source priority as a tie-breaker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from src.intelligence import attach_intelligence


@dataclass(frozen=True)
class CompletenessField:
    name: str
    weight: int
    alternatives: tuple[str, ...] = ()


FIELDS = (
    CompletenessField("title", 12),
    CompletenessField("start_date", 12),
    CompletenessField("start_time", 10),
    CompletenessField("venue", 10, ("venue_id", "venue_registry_name")),
    CompletenessField("city", 8),
    CompletenessField("url", 8, ("external_url", "eventbrite_url")),
    CompletenessField("description", 8),
    CompletenessField("organization", 5, ("organizer", "host")),
    CompletenessField("address", 5),
    CompletenessField("category", 5),
    CompletenessField("image_url", 4),
    CompletenessField("cost", 4),
    CompletenessField("schedule_items", 4),
    CompletenessField("registration_info", 3, ("registration_url",)),
    CompletenessField("end_time", 2),
)

TOTAL_WEIGHT = sum(field.weight for field in FIELDS)


def score_event_completeness(event: dict[str, Any]) -> dict[str, Any]:
    """Return score details without mutating the event."""
    present: list[str] = []
    missing: list[str] = []
    earned = 0
    for field in FIELDS:
        if _has_any(event, (field.name, *field.alternatives)):
            present.append(field.name)
            earned += field.weight
        else:
            missing.append(field.name)
    score = round(earned / TOTAL_WEIGHT, 4) if TOTAL_WEIGHT else 0.0
    return {
        "score": score,
        "percent": round(score * 100),
        "present_fields": present,
        "missing_fields": missing,
        "earned_weight": earned,
        "total_weight": TOTAL_WEIGHT,
    }


def enrich_event_completeness(event: dict[str, Any]) -> dict[str, Any]:
    """Attach completeness metadata and explainable intelligence."""
    result = dict(event)
    details = score_event_completeness(result)
    result["completeness_score"] = details["score"]
    result["completeness_percent"] = details["percent"]
    result["completeness_missing"] = details["missing_fields"]
    return attach_intelligence(
        result,
        "completeness",
        details,
        1.0,
        "weighted_field_presence",
    )


def completeness_rank(event: dict[str, Any]) -> tuple[float, int]:
    """Return a stable ranking tuple for canonical record selection."""
    raw = event.get("completeness_score")
    try:
        score = float(raw)
    except (TypeError, ValueError):
        score = float(score_event_completeness(event)["score"])
    populated = sum(1 for value in event.values() if _present(value))
    return score, populated


def summarize_completeness(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [score_event_completeness(event) for event in events]
    if not rows:
        return {"event_count": 0, "average_percent": 0, "missing_counts": {}}
    missing_counts: dict[str, int] = {}
    for row in rows:
        for field in row["missing_fields"]:
            missing_counts[field] = missing_counts.get(field, 0) + 1
    return {
        "event_count": len(rows),
        "average_percent": round(sum(row["percent"] for row in rows) / len(rows), 1),
        "missing_counts": dict(sorted(missing_counts.items(), key=lambda item: (-item[1], item[0]))),
    }


def _has_any(event: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return any(_present(event.get(field)) for field in fields)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True
