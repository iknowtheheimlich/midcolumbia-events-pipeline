"""Upsert final classified events into the durable JSONL history corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.classified_history import load_jsonl, merge_classified_history, write_jsonl
from src.event_io import load_event_records


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
    merged, stats = merge_classified_history(existing, load_event_records(args.input))
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
