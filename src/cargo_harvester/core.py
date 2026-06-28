from __future__ import annotations

import csv
from pathlib import Path

from cargo_harvester.models import CANONICAL_FIELDS, EventRecord


def dedupe_events(events: list[EventRecord]) -> list[EventRecord]:
    seen: set[str] = set()
    output: list[EventRecord] = []
    for event in events:
        if event.dedupe_key in seen:
            continue
        seen.add(event.dedupe_key)
        output.append(event)
    return output


def write_events_csv(events: list[EventRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        for event in events:
            writer.writerow(event.to_csv_row())
