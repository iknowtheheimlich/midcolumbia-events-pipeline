"""Deduplicate real multi-source publisher-ready fixture output.

Usage:
    python -m tools.deduplicate_real_multi_source
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from src.deduplicate import deduplicate_events

DEFAULT_INPUT = Path("fixtures/real_multi_source/publisher_ready_events.json")
DEFAULT_OUTPUT = Path("fixtures/real_multi_source/deduplicated_publisher_ready_events.json")
DEFAULT_REPORT = Path("fixtures/real_multi_source/deduplication_report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate real multi-source publisher-ready events")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    events = load_json_fixture(args.input)
    if not isinstance(events, list):
        raise TypeError("publisher-ready fixture must be a list")

    result = deduplicate_events(events)
    save_json_fixture(args.output, result.events)
    save_json_fixture(args.report, result.duplicate_groups)

    print({"input_events": len(events), **result.counts})
    print(f"Deduplicated events: {args.output}")
    print(f"Deduplication report: {args.report}")


if __name__ == "__main__":
    main()
