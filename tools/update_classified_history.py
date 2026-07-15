"""Upsert final classified events into the durable JSONL history corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.classified_history import load_jsonl, merge_classified_history, write_jsonl


def load_events(path: Path) -> list[dict]:
    if path.suffix.casefold() == ".jsonl":
        return load_jsonl(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("events", "all_events", "publisher_ready_events", "deduplicated_publisher_ready_events"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    raise ValueError(f"No event list found in {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON or JSONL containing final classified events")
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("history/classified_events.jsonl"),
        help="Durable corpus path",
    )
    args = parser.parse_args()

    existing = load_jsonl(args.history)
    merged, stats = merge_classified_history(existing, load_events(args.input))
    write_jsonl(args.history, merged)

    print("Attempt 77 Classified History Corpus")
    print("====================================")
    print(f"Existing events: {stats['existing']}")
    print(f"Incoming classified: {stats['incoming']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped unclassified: {stats['skipped_unclassified']}")
    print(f"Corpus total: {stats['total']}")
    print(f"History path: {args.history}")


if __name__ == "__main__":
    main()
