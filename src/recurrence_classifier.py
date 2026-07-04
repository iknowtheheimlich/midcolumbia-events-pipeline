"""Shared event recurrence and event-kind classification."""

from __future__ import annotations

from datetime import date
from typing import Any

SERIES_KEYWORDS = (
    "every ",
    "weekly",
    "monthly",
    "series",
    "each ",
    "thursdays",
    "wednesdays",
    "tuesdays",
    "mondays",
    "fridays",
    "saturdays",
    "sundays",
)


def classify_event_kind(event: dict[str, Any]) -> str:
    """Classify a normalized event as single, multi_day, series, or unknown.

    This function is intentionally conservative. Series containers are safer in
    a review queue than in a chronological publisher pretending they are one
    giant event.
    """
    start = parse_date(event.get("start_date"))
    end = parse_date(event.get("end_date"))
    recurrence_note = str(event.get("recurrence_note") or "").strip()
    title = str(event.get("title") or "").strip()
    description = str(event.get("description") or "").strip()

    if has_series_signal(recurrence_note, title, description):
        return "series"

    if start and end:
        duration_days = (end - start).days + 1
        if duration_days <= 0:
            return "unknown"
        if duration_days == 1:
            return "single"
        if duration_days <= 4:
            return "multi_day"
        return "series"

    if start and not end:
        return "single"

    return "unknown"


def has_series_signal(*values: str) -> bool:
    """Return true when text strongly suggests recurring event series."""
    combined = " ".join(value.lower() for value in values if value)
    if not combined:
        return False
    return any(keyword in combined for keyword in SERIES_KEYWORDS)


def parse_date(value: Any) -> date | None:
    """Parse ISO date safely."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def split_publisher_ready(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split events into publisher-ready and recurrence review queues."""
    publisher_ready: list[dict[str, Any]] = []
    recurrence_review: list[dict[str, Any]] = []

    for event in events:
        event_kind = event.get("event_kind") or classify_event_kind(event)
        event_with_kind = dict(event)
        event_with_kind["event_kind"] = event_kind

        if event_kind == "series":
            recurrence_review.append(event_with_kind)
        else:
            publisher_ready.append(event_with_kind)

    return publisher_ready, recurrence_review
