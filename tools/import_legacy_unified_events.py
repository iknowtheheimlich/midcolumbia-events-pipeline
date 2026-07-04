"""Import legacy unified_events.csv into canonical JSON fixture.

Usage:
    python -m tools.import_legacy_unified_events --input "D:\\Carls_Instructions\\Mission_Control\\Reddit\\Instructions\\output\\unified_events.csv"
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from adapters.algolia.fixtures import save_json_fixture

DEFAULT_OUTPUT = Path("fixtures/legacy/normalized_events.json")

FIELD_ALIASES = {
    "title": ("title", "event_title", "name"),
    "venue": ("venue", "venue_name", "location"),
    "venue_id": ("venue_id", "canonical_venue_id", "place_id"),
    "address": ("address", "venue_address"),
    "city": ("city",),
    "start_date": ("start_date", "date"),
    "end_date": ("end_date",),
    "start_time": ("start_time", "time"),
    "end_time": ("end_time",),
    "url": ("url", "source_url", "event_url"),
    "source": ("source",),
    "category": ("category", "event_category"),
    "description": ("description", "summary"),
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
    return {
        "title": value_for(row, "title"),
        "venue": value_for(row, "venue"),
        "venue_id": nullable(value_for(row, "venue_id")),
        "address": nullable(value_for(row, "address")),
        "city": value_for(row, "city"),
        "start_date": value_for(row, "start_date"),
        "end_date": nullable(value_for(row, "end_date")),
        "start_time": nullable(value_for(row, "start_time")),
        "end_time": nullable(value_for(row, "end_time")),
        "url": value_for(row, "url"),
        "source": value_for(row, "source") or "LegacyUnifiedCSV",
        "category": nullable(value_for(row, "category")),
        "description": nullable(value_for(row, "description")),
    }


def value_for(row: dict[str, Any], field: str) -> str:
    for candidate in FIELD_ALIASES[field]:
        if candidate in row and row[candidate] not in (None, ""):
            return str(row[candidate]).strip()
    return ""


def nullable(value: str) -> str | None:
    text = value.strip() if value else ""
    return text or None


if __name__ == "__main__":
    main()
