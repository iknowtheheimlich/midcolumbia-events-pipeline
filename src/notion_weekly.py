"""Normalize exported Notion weekly-event rows into pipeline source events.

Weekly rows are treated as a curated recurrence source. Only rows explicitly marked
Weekly and Generate This Week are materialized, and only when a weekday or explicit
date can place the occurrence inside the requested publication window.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any, Iterable


_TRUE_VALUES = {True, 1, "1", "true", "yes", "__YES__"}
_WEEKDAY_INDEX = {
    "monday": 0,
    "mondays": 0,
    "mon": 0,
    "tuesday": 1,
    "tuesdays": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wednesdays": 2,
    "wed": 2,
    "thursday": 3,
    "thursdays": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fridays": 4,
    "fri": 4,
    "saturday": 5,
    "saturdays": 5,
    "sat": 5,
    "sunday": 6,
    "sundays": 6,
    "sun": 6,
}
_MARKDOWN_VENUE_RE = re.compile(
    r"^\[(?P<label>[^]]+)]\((?P<url>[^)]+)\)(?:,\s*(?P<city>.+))?$"
)
_WEEKDAY_SPLIT_RE = re.compile(r"\s*(?:&|,|/|\band\b)\s*", re.IGNORECASE)


def load_notion_weekly_rows(path: Path) -> list[dict[str, Any]]:
    """Load a Notion weekly export from JSON or CSV."""
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
            rows = payload["results"]
        else:
            raise ValueError("Notion weekly JSON must be a row list or contain a results list")
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError("Notion weekly export rows must be objects")
        return [dict(row) for row in rows]
    raise ValueError("Notion weekly export must be .csv or .json")


def materialize_weekly_events(
    rows: Iterable[dict[str, Any]],
    *,
    week_start: date,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Return canonical source events generated from eligible Notion rows."""
    if days < 1:
        raise ValueError("days must be at least 1")

    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    week_end = week_start + timedelta(days=days)

    for row in rows:
        if not _truthy(row.get("Weekly")) or not _truthy(row.get("Generate This Week")):
            continue

        event_dates = _resolve_dates(row, week_start, week_end)
        if not event_dates:
            continue

        title = _text(row.get("Event Name"))
        reddit_combo = _text(row.get("Venue Reddit Combo"))
        combo_venue, combo_url, combo_city = _parse_reddit_combo(reddit_combo)
        venue = _text(row.get("Venue")) or _text(row.get("Venue Name")) or combo_venue
        venue_url = _text(row.get("Venue URL")) or _text(row.get("Website")) or combo_url
        city = _text(row.get("City")) or combo_city
        time_notes = _text(row.get("Time, Price, Notes"))
        if not title or not venue:
            continue

        start_time, end_time = _parse_time_range(time_notes)
        for event_date in event_dates:
            key = (title.casefold(), venue.casefold(), event_date.isoformat(), start_time or "")
            if key in seen:
                continue
            seen.add(key)

            event = {
                "title": title,
                "start_date": event_date.isoformat(),
                "start_time": start_time,
                "end_time": end_time,
                "venue": venue,
                "city": city,
                "url": venue_url,
                "source": "NotionWeekly",
                "category": "Weekly Events",
                "description": _text(row.get("Notes Recurring")),
                "publication_target": "MAIN",
                "is_weekly": True,
                "time_price_notes": time_notes,
            }
            if reddit_combo:
                event["venue_reddit_combo"] = reddit_combo
            events.append(event)

    return events


def _resolve_dates(row: dict[str, Any], week_start: date, week_end: date) -> list[date]:
    explicit = _parse_date(row.get("Date")) or _parse_date(row.get("date:Date:start"))
    if explicit is not None:
        return [explicit] if week_start <= explicit < week_end else []

    dates: list[date] = []
    for weekday in _weekdays(row.get("Days of the Week")):
        offset = (weekday - week_start.weekday()) % 7
        candidate = week_start + timedelta(days=offset)
        if candidate < week_end and candidate not in dates:
            dates.append(candidate)
    return sorted(dates)


def _weekdays(value: Any) -> list[int]:
    text = _text(value).casefold().strip(" .")
    if not text:
        return []
    weekdays: list[int] = []
    for token in _WEEKDAY_SPLIT_RE.split(text):
        weekday = _WEEKDAY_INDEX.get(token.strip(" ."))
        if weekday is not None and weekday not in weekdays:
            weekdays.append(weekday)
    return weekdays


def _parse_date(value: Any) -> date | None:
    text = _text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_time_range(value: str) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    token = value.split(" ", 1)[0].strip()
    if "-" in token:
        start, end = token.split("-", 1)
        shared_suffix = (
            end.strip().casefold()[-1:]
            if end.strip().casefold().endswith(("a", "p"))
            else ""
        )
        if shared_suffix and not start.strip().casefold().endswith(("a", "p")):
            start = f"{start}{shared_suffix}"
        return _normalize_time(start), _normalize_time(end)
    return _normalize_time(token), None


def _normalize_time(value: str) -> str | None:
    text = value.strip().casefold().replace(".", "")
    if not text:
        return None
    suffix = ""
    if text.endswith(("a", "p")):
        suffix = text[-1]
        text = text[:-1]
    try:
        hour_text, minute_text = (text.split(":", 1) + ["00"])[:2]
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return None
    if suffix == "p" and hour != 12:
        hour += 12
    elif suffix == "a" and hour == 12:
        hour = 0
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _parse_reddit_combo(value: str) -> tuple[str, str, str]:
    match = _MARKDOWN_VENUE_RE.match(value.strip()) if value else None
    if not match:
        return "", "", ""
    return (
        match.group("label").strip(),
        match.group("url").strip(),
        (match.group("city") or "").strip(),
    )


def _truthy(value: Any) -> bool:
    return value in _TRUE_VALUES or (
        isinstance(value, str)
        and value.strip().casefold() in {"true", "yes", "__yes__"}
    )


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""
