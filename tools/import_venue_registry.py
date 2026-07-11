"""Import a Notion Ultimate Venues CSV export into a deterministic lookup artifact."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.venue_registry import VenueRecord, VenueRegistry


DEFAULT_INPUT = Path("input/Ultimate Venues.csv")
DEFAULT_OUTPUT = Path("generated/venue_registry/registry.json")
DEFAULT_SUMMARY = Path("generated/venue_registry/import_summary.txt")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def load_notion_csv(path: Path) -> VenueRegistry:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Venue Name", "Official Name", "Address", "Place ID", "Plus Code", "Venue Website", "Venue Type Description"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing expected Notion columns: {', '.join(sorted(missing))}")

        records: list[VenueRecord] = []
        for row in reader:
            venue_name = _clean(row.get("Venue Name"))
            if not venue_name:
                continue
            records.append(
                VenueRecord(
                    venue_name=venue_name,
                    official_name=_clean(row.get("Official Name")),
                    address=_clean(row.get("Address")),
                    place_id=_clean(row.get("Place ID")),
                    plus_code=_clean(row.get("Plus Code")),
                    website=_clean(row.get("Venue Website")),
                    venue_type=_clean(row.get("Venue Type Description")),
                    reddit_combo=_clean(row.get("Venue Reddit Combo")),
                )
            )
    return VenueRegistry(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    registry = load_notion_csv(args.csv_path)
    registry.to_json(args.output)

    with_place_id = sum(bool(record.place_id) for record in registry.records)
    with_address = sum(bool(record.address) for record in registry.records)
    with_website = sum(bool(record.website) for record in registry.records)
    summary = (
        "Attempt_26 Venue Registry Import\n"
        "================================\n\n"
        f"Source CSV: {args.csv_path}\n"
        f"Records: {len(registry.records)}\n"
        f"With Place ID: {with_place_id}\n"
        f"With address: {with_address}\n"
        f"With website: {with_website}\n"
        f"Output: {args.output}\n"
    )
    DEFAULT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_SUMMARY.write_text(summary, encoding="utf-8")
    print(summary, end="")


if __name__ == "__main__":
    main()
