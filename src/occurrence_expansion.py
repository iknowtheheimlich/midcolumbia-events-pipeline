"""Expand supported source date ranges into canonical daily occurrences."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any, Iterable, Mapping

from src.occurrence_identity import canonical_occurrence_identity
from src.recurrence_classifier import classify_event_kind, parse_date


def expand_multi_day_occurrences(
    events: Iterable[dict[str, Any]], *, week_start: date, days: int = 7
) -> list[dict[str, Any]]:
    """Expand supported ``multi_day`` ranges, clipped to the publication week."""
    if days < 1:
        raise ValueError("publication days must be at least 1")
    week_end = week_start + timedelta(days=days)
    output: list[dict[str, Any]] = []
    for event in events:
        event_kind = classify_event_kind(event)
        if event_kind != "multi_day":
            occurrence = parse_date(event.get("start_date"))
            output.append(
                _canonical_single_occurrence(event, occurrence)
                if event_kind == "single" and occurrence is not None
                else event
            )
            continue
        source_start = parse_date(event.get("start_date"))
        source_end = parse_date(event.get("end_date"))
        if source_start is None or source_end is None or source_end < source_start:
            output.append(event)
            continue
        first = max(source_start, week_start)
        last = min(source_end, week_end - timedelta(days=1))
        if first > last:
            continue
        current = first
        while current <= last:
            output.append(_expanded_occurrence(event, current, source_start, source_end))
            current += timedelta(days=1)
    return output


def _canonical_single_occurrence(event: dict[str, Any], occurrence: date) -> dict[str, Any]:
    copied = deepcopy(event)
    occurrence_text = occurrence.isoformat()
    copied["occurrence_date"] = occurrence_text
    copied["occurrence_identity"] = canonical_occurrence_identity(copied, occurrence_text)
    copied.setdefault("source_start_date", occurrence_text)
    copied.setdefault("source_end_date", str(event.get("end_date") or occurrence_text))
    copied.setdefault("source_time_evidence", _source_time_evidence(event))
    return copied


def _expanded_occurrence(
    event: dict[str, Any], occurrence: date, source_start: date, source_end: date
) -> dict[str, Any]:
    copied = deepcopy(event)
    occurrence_text = occurrence.isoformat()
    copied["source_start_date"] = source_start.isoformat()
    copied["source_end_date"] = source_end.isoformat()
    copied["source_time_evidence"] = _source_time_evidence(event)
    copied["occurrence_date"] = occurrence_text
    copied["start_date"] = occurrence_text
    copied["end_date"] = occurrence_text
    copied["event_kind"] = "single"
    copied["occurrence_identity"] = canonical_occurrence_identity(copied, occurrence_text)
    _apply_day_specific_time(copied, event, occurrence_text)
    return copied


def _source_time_evidence(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "start_time": event.get("start_time"),
        "end_time": event.get("end_time"),
        "all_day": event.get("all_day"),
        "time_semantics": deepcopy(event.get("time_semantics")),
        "intelligence": deepcopy((event.get("intelligence") or {}).get("time_semantics")),
    }


def _apply_day_specific_time(
    copied: dict[str, Any], source: Mapping[str, Any], occurrence_date: str
) -> None:
    schedule = source.get("occurrence_times") or source.get("daily_times")
    if not isinstance(schedule, Mapping):
        return
    evidence = schedule.get(occurrence_date)
    if not isinstance(evidence, Mapping):
        return
    for field in ("start_time", "end_time", "all_day"):
        if field in evidence:
            copied[field] = evidence[field]
