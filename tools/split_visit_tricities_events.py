"""Split normalized Visit Tri-Cities events into publisher-ready and recurrence-review files.

Usage:
    python -m tools.split_visit_tricities_events

Reads:
    fixtures/visit_tricities/normalized_events.json

Writes:
    fixtures/visit_tricities/publisher_ready_events.json
    fixtures/visit_tricities/series_review_queue.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from src.recurrence_classifier import split_publisher_ready

DEFAULT_INPUT = Path("fixtures/visit_tricities/normalized_events.json")
DEFAULT_READY = Path("fixtures/visit_tricities/publisher_ready_events.json")
DEFAULT_REVIEW = Path("fixtures/visit_tricities/series_review_queue.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split Visit Tri-Cities events for publisher safety")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input normalized JSON")
    parser.add_argument("--publisher-ready", type=Path, default=DEFAULT_READY, help="Publisher-ready output path")
    parser.add_argument("--series-review", type=Path, default=DEFAULT_REVIEW, help="Series review output path")
    args = parser.parse_args()

    events = load_json_fixture(args.input)
    if not isinstance(events, list):
        raise TypeError("normalized events fixture must be a list")

    publisher_ready, recurrence_review = split_publisher_ready(events)
    save_json_fixture(args.publisher_ready, publisher_ready)
    save_json_fixture(args.series_review, recurrence_review)

    print(f"Publisher-ready events: {len(publisher_ready)} -> {args.publisher_ready}")
    print(f"Series review events: {len(recurrence_review)} -> {args.series_review}")


if __name__ == "__main__":
    main()
