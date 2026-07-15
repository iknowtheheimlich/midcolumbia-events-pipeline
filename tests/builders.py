"""Shared builders for review-operations tests."""

from __future__ import annotations

from typing import Any


def build_event(
    event_id: str = "1",
    *,
    title: str = "Example",
    category: str = "Sports",
    confidence: float = 0.4,
    needs_review: bool = True,
    **overrides: Any,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_id": event_id,
        "title": title,
        "category": category,
        "category_confidence": confidence,
        "category_confidence_band": "low",
        "category_reason": "description_rule=sports",
        "category_needs_review": needs_review,
    }
    event.update(overrides)
    return event


def build_backlog(
    event_id: str = "1",
    *,
    title: str = "Example",
    category: str = "Sports",
    confidence: float = 0.4,
    first_seen: str = "2026-07-01",
    last_seen: str = "2026-07-15",
    appearances: int = 1,
    status: str = "recurring",
    **overrides: Any,
) -> dict[str, dict[str, Any]]:
    row: dict[str, Any] = {
        "event_id": event_id,
        "title": title,
        "category": category,
        "confidence": confidence,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "appearances": appearances,
        "status": status,
    }
    row.update(overrides)
    return {f"{event_id}|{category}": row}
