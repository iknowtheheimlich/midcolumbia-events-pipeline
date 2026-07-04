"""Import legacy unified_events.csv into canonical JSON fixture.

Usage:
    python -m tools.import_legacy_unified_events --input "D:\\Carls_Instructions\\Mission_Control\\Reddit\\Instructions\\output\\unified_events.csv"
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from adapters.algolia.fixtures import save_json_fixture

DEFAULT_OUTPUT = Path("fixtures/legacy/normalized_events.json")

FIELD_ALIASES = {
    "title": ("Event Name", "title", "event_title", "name"),
    "venue": ("Canonical Venue", "Venue", "venue", "venue_name", "location"),
    "venue_id": ("Google Place ID", "venue_id", "canonical_venue_id", "place_id"),
    "address": ("Canonical Address", "Address", "address", "venue_address"),
    "city": ("City", "city"),
    "start_date": ("start_date", "date"),
    "date_raw": ("Date Raw",),
    "end_date": ("end_date",),
    "start_time": ("Start Time", "start_time", "time"),
    "end_time": ("End Time", "end_time"),
    "url": ("Source URL", "url", "source_url", "event_url"),
    "source": ("Source", "source"),
    "category": ("Category", "category", "event_category"),
    "description": ("Description", "description", "summary"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy unified events CSV")
    parser.add_argument("--input", required=True, type=Path, help="Legacy unified_events.csv path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON fixture path")
    args = parser.parse_args()

    events = read_legacy_csv(args.input)
    save_json_fixture(args.output, events)
    print(f"Imported {len(events)} events -> {args.output}")


def read_legacy_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    return [normalize_row(row) for row in rows]


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    start_date = value_for(row, "start_date") or parse_legacy_date(value_for(row, "date_raw"))
    return {
        "title": value_for(row, "title"),
        "venue": value_for(row, "venue"),
        "venue_id": nullable(value_for(row, "venue_id")),
        "address": nullable(value_for(row, "address")),
        "city": value_for(row, "city"),
        "start_date": start_date,
        "end_date": nullable(value_for(row, "end_date")) or start_date,
        "start_time": nullable(parse_legacy_time(value_for(row, "start_time"))),
        "end_time": nullable(parse_legacy_time(value_for(row, "end_time"))),
        "url": value_for(row, "url"),
        "source": value_for(row, "source") or "LegacyUnifiedCSV",
        "category": nullable(value_for(row, "category")),
        "description": nullable(value_for(row, "description")),
        "legacy_dedupe_key": nullable(row.get("Dedupe Key", "")),
        "legacy_reddit_include": nullable(row.get("Reddit Include", "")),
        "legacy_needs_review": nullable(row.get("Needs Review", "")),
        "legacy_venue_match_status": nullable(row.get("Venue Match Status", "")),
    }


def value_for(row: dict[str, Any], field: str) -> str:
    for candidate in FIELD_ALIASES[field]:
        if candidate in row and row[candidate] not in (None, ""):
            return str(row[candidate]).strip()
    return ""


def parse_legacy_date(value: str) -> str:
    text = value.strip() if value else ""
    if not text:
        return ""

    for fmt in ("%a, %d %b, %Y", "%d %b, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def parse_legacy_time(value: str) -> str:
    text = value.strip() if value else ""
    if not text:
        return ""

    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return text


def nullable(value: str) -> str | None:
    text = value.strip() if value else ""
    return text or None


if __name__ == "__main__":
    main()
