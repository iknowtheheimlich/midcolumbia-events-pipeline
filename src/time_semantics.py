"""Normalize canonical event time meaning before publisher projection.

Attempt_46_TimeSemantics

Collectors frequently coerce date-only and unknown-end values into clock times. This
layer converts those transport artifacts into explicit event semantics while preserving
legitimate midnight events when no all-day evidence exists.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta, timezone

from src.intelligence import attach_intelligence

_DATE_ONLY_SOURCES = {"allevents"}
_MIDNIGHT_VALUES = {"00:00", "00:00:00", "12:00 AM", "12:00AM"}
_END_OF_DAY_VALUES = {"23:59", "23:59:00", "11:59 PM", "11:59PM"}


def enrich_event_time_semantics(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copied event with explicit all-day and unknown-end semantics."""
    copied = dict(event)
    start = _time(copied.get("start_time"))
    end = _time(copied.get("end_time"))
    source = str(copied.get("source") or "").strip().casefold()
    explicit_all_day = _truthy(copied.get("all_day")) or _truthy(copied.get("is_all_day"))
    date_only = _truthy(copied.get("date_only")) or _truthy(copied.get("start_date_only"))
    reasons: list[str] = []

    all_day = explicit_all_day or date_only
    range_boundary = _range_boundary_sentinel(copied, source)
    day_boundary = start in _MIDNIGHT_VALUES and end in _END_OF_DAY_VALUES and _same_day(copied)
    if explicit_all_day:
        reasons.append("explicit_all_day")
    elif date_only:
        reasons.append("date_only_marker")
    elif range_boundary or day_boundary:
        copied["time_unknown"] = True
        copied["start_time"] = None
        copied["end_time"] = None
        reasons.append("range_boundary_sentinel" if range_boundary else "date_boundary_sentinel")
    elif source in _DATE_ONLY_SOURCES and start in _MIDNIGHT_VALUES and (
        end is None or end in _MIDNIGHT_VALUES
    ):
        # Compatibility repair for normalized AllEvents snapshots created before
        # Attempt_45 stopped coercing date-only JSON-LD into midnight.
        all_day = True
        reasons.append("legacy_source_date_only_midnight")
    elif start in _MIDNIGHT_VALUES and end in _MIDNIGHT_VALUES and _same_day(copied):
        all_day = True
        reasons.append("midnight_to_midnight_same_day")

    if all_day:
        copied["all_day"] = True
        copied["start_time"] = "All day"
        copied["end_time"] = None
        reasons.append("clock_times_replaced_with_all_day")
    else:
        copied["all_day"] = False
        if end in _END_OF_DAY_VALUES:
            copied["end_time"] = None
            reasons.append("synthetic_end_of_day_removed")
        if start and end and _normalized_clock(start) == _normalized_clock(end):
            copied["end_time"] = None
            reasons.append("identical_end_removed")

    if _exclusive_midnight_end(copied):
        copied["exclusive_end_date"] = True
        reasons.append("exclusive_midnight_end")

    reason = "+".join(reasons) if reasons else "unchanged"
    value = {
        "all_day": bool(copied.get("all_day")),
        "start_time": copied.get("start_time"),
        "end_time": copied.get("end_time"),
    }
    return attach_intelligence(copied, "time_semantics", value, 1.0, reason)


def _time(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalized_clock(value: str) -> str:
    text = value.strip().upper().replace(" ", "")
    aliases = {
        "12:00AM": "00:00",
        "12:00PM": "12:00",
        "00:00:00": "00:00",
        "23:59:00": "23:59",
    }
    return aliases.get(text, text)


def _same_day(event: dict[str, Any]) -> bool:
    start_date = str(event.get("start_date") or "").strip()
    end_date = str(event.get("end_date") or start_date).strip()
    return bool(start_date and start_date == end_date)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "all_day", "all-day"}


def _exclusive_midnight_end(event: dict[str, Any]) -> bool:
    start_date = str(event.get("start_date") or "").strip()
    end_date = str(event.get("end_date") or "").strip()
    if _time(event.get("end_time")) not in _MIDNIGHT_VALUES or not start_date or not end_date:
        return False
    try:
        return datetime.fromisoformat(end_date).date() == datetime.fromisoformat(start_date).date() + timedelta(days=1)
    except ValueError:
        return False


def _range_boundary_sentinel(event: dict[str, Any], source: str) -> bool:
    """Recognize API range endpoints that are not per-occurrence clock times."""
    if source != "allevents":
        return False
    try:
        start_stamp = int(event.get("source_start_timestamp"))
        end_stamp = int(event.get("source_end_timestamp"))
    except (TypeError, ValueError):
        return False
    if end_stamp - start_stamp < 86400:
        return False
    offset_text = str(event.get("source_timezone") or event.get("timezone") or "").strip()
    try:
        sign = -1 if offset_text.startswith("-") else 1
        hours, minutes = (int(part) for part in offset_text.lstrip("+-").split(":"))
        offset = timezone(sign * timedelta(hours=hours, minutes=minutes))
    except (TypeError, ValueError):
        return False
    local_start = datetime.fromtimestamp(start_stamp, timezone.utc).astimezone(offset)
    local_end = datetime.fromtimestamp(end_stamp, timezone.utc).astimezone(offset)
    return local_start.strftime("%H:%M") == "00:00" and local_end.strftime("%H:%M") in {"00:00", "00:59", "23:59"}
