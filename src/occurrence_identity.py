"""Canonical source-occurrence identity shared by pipeline and curation."""

from __future__ import annotations

from typing import Any, Mapping


def canonical_occurrence_identity(
    row: Mapping[str, Any], occurrence_date: str, *, week: str | None = None
) -> str:
    source = _norm(row.get("Source") or row.get("source"))
    event_id = _norm(row.get("Source Event ID") or row.get("source_event_id"))
    prefix = f"v1|{week}|" if week is not None else "v1|"
    if event_id:
        return f"{prefix}{source.casefold()}|id:{event_id}|{occurrence_date}"
    title = _norm(row.get("Original Title") or row.get("Title") or row.get("title"))
    venue = _norm(row.get("Venue") or row.get("venue"))
    original_time = _norm(row.get("Original Time") or _time(row) or row.get("start_time"))
    stable = "|".join((title.casefold(), venue.casefold(), original_time))
    return f"{prefix}{source.casefold()}|fallback:{stable}|{occurrence_date}"


def _time(row: Mapping[str, Any]) -> str:
    start = _norm(row.get("Start Time"))
    end = _norm(row.get("End Time"))
    return f"{start}-{end}" if start and end else start


def _norm(value: object) -> str:
    return " ".join(str(value or "").strip().split())
