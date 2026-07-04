"""Run multiple source fixtures through the unified pipeline spine.

Usage:
    python -m tools.run_multi_source_pipeline
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from adapters.visit_tricities.config import SOURCE_NAME as VTC_SOURCE_NAME
from src.pipeline import SourceBatch, run_pipeline

DEFAULT_VTC_INPUT = Path("fixtures/visit_tricities/normalized_events.json")
DEFAULT_MOCK_INPUT = Path("fixtures/mock_source/events.json")
DEFAULT_READY = Path("fixtures/multi_source/publisher_ready_events.json")
DEFAULT_REVIEW = Path("fixtures/multi_source/series_review_queue.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-source unified pipeline smoke test")
    parser.add_argument("--vtc-input", type=Path, default=DEFAULT_VTC_INPUT, help="Visit Tri-Cities normalized events")
    parser.add_argument("--mock-input", type=Path, default=DEFAULT_MOCK_INPUT, help="Mock source normalized events")
    parser.add_argument("--publisher-ready", type=Path, default=DEFAULT_READY, help="Publisher-ready output path")
    parser.add_argument("--series-review", type=Path, default=DEFAULT_REVIEW, help="Series review output path")
    args = parser.parse_args()

    vtc_events = load_json_fixture(args.vtc_input)
    mock_events = load_json_fixture(args.mock_input)

    if not isinstance(vtc_events, list):
        raise TypeError("Visit Tri-Cities fixture must be a list")
    if not isinstance(mock_events, list):
        raise TypeError("Mock source fixture must be a list")

    result = run_pipeline(
        [
            SourceBatch(source_name=VTC_SOURCE_NAME, events=vtc_events),
            SourceBatch(source_name="MockSource", events=mock_events),
        ]
    )

    save_json_fixture(args.publisher_ready, result.publisher_ready_events)
    save_json_fixture(args.series_review, result.recurrence_review_events)

    print(result.counts)
    print(f"Publisher-ready: {args.publisher_ready}")
    print(f"Series review: {args.series_review}")


if __name__ == "__main__":
    main()
