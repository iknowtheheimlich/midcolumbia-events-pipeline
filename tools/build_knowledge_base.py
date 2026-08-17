"""Build knowledge artifacts from an exported historical Reddit database."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.historical_corpus import build_historical_corpus, load_historical_rows, write_historical_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-corpus", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("generated/corpus"))
    args = parser.parse_args()

    if not args.historical_corpus.exists():
        parser.error(f"historical corpus not found: {args.historical_corpus}")

    rows = load_historical_rows(args.historical_corpus)
    result = build_historical_corpus(rows)
    paths = write_historical_corpus(result, args.output_dir)

    summary = result.summary()
    print("Knowledge Build Summary")
    print("-----------------------")
    print(f"Historical Events.............{summary['historical_rows']}")
    print(f"Unique Venues................{summary['unique_venues']}")
    print(f"Unique Hosts.................{summary['unique_hosts']}")
    print(f"Artist Candidates............{summary['artist_candidates']}")
    print(f"Recurring Families...........{summary['recurring_families']}")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
