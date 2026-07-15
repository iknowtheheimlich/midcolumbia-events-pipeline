"""Restore a classified history corpus from a JSONL snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.classified_history import load_jsonl
from src.corpus_snapshots import corpus_checksum, restore_corpus_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Snapshot JSONL file to restore")
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("history/classified_events.jsonl"),
        help="Active corpus path",
    )
    args = parser.parse_args()

    rows = load_jsonl(args.snapshot)
    restore_corpus_snapshot(args.snapshot, args.history)

    print("Attempt 79 Corpus Restore")
    print("=========================")
    print(f"Restored events: {len(rows)}")
    print(f"Snapshot: {args.snapshot}")
    print(f"History path: {args.history}")
    print(f"Checksum: {corpus_checksum(args.history)}")


if __name__ == "__main__":
    main()
