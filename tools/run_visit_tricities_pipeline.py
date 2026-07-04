"""Run Visit Tri-Cities fixture through the unified pipeline spine.

Usage:
    python -m tools.run_visit_tricities_pipeline
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from adapters.visit_tricities.config import SOURCE_NAME
from src.pipeline import SourceBatch, run_pipeline

DEFAULT_INPUT = Path("fixtures/visit_tricities/normalized_events.json")
DEFAULT_READY = Path("fixtures/visit_tricities/pipeline_publisher_ready_events.json")
DEFAULT_REVIEW = Path("fixtures/visit_tricities/pipeline_series_review_queue.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Visit Tri-Cities through unified pipeline")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input normalized events")
    parser.add_argument("--publisher-ready", type=Path, default=DEFAULT_READY, help="Publisher-ready output path")
    parser.add_argument("--series-review", type=Path, default=DEFAULT_REVIEW, help="Series review output path")
    args = parser.parse_args()

    events = load_json_fixture(args.input)
    if not isinstance(events, list):
        raise TypeError("normalized events fixture must be a list")

    result = run_pipeline([SourceBatch(source_name=SOURCE_NAME, events=events)])
    save_json_fixture(args.publisher_ready, result.publisher_ready_events)
    save_json_fixture(args.series_review, result.recurrence_review_events)

    print(result.counts)
    print(f"Publisher-ready: {args.publisher_ready}")
    print(f"Series review: {args.series_review}")


if __name__ == "__main__":
    main()
