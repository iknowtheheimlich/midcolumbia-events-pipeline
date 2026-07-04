"""Run Visit Tri-Cities and legacy/Allevents fixtures through the unified pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from adapters.visit_tricities.config import SOURCE_NAME as VTC_SOURCE_NAME
from src.pipeline import SourceBatch, run_pipeline

DEFAULT_VTC_INPUT = Path("fixtures/visit_tricities/normalized_events.json")
DEFAULT_SECOND_INPUT = Path("fixtures/allevents/normalized_events.json")
DEFAULT_READY_OUTPUT = Path("fixtures/real_multi_source/publisher_ready_events.json")
DEFAULT_DEDUPED_OUTPUT = Path("fixtures/real_multi_source/deduplicated_publisher_ready_events.json")
DEFAULT_DEDUPE_REPORT = Path("fixtures/real_multi_source/deduplication_report.json")
DEFAULT_REVIEW_OUTPUT = Path("fixtures/real_multi_source/series_review_queue.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real source fixtures through unified pipeline")
    parser.add_argument("--vtc-input", type=Path, default=DEFAULT_VTC_INPUT)
    parser.add_argument("--second-input", type=Path, default=DEFAULT_SECOND_INPUT)
    parser.add_argument("--second-source-name", default="Allevents")
    parser.add_argument("--publisher-ready", type=Path, default=DEFAULT_READY_OUTPUT)
    parser.add_argument("--deduplicated", type=Path, default=DEFAULT_DEDUPED_OUTPUT)
    parser.add_argument("--dedupe-report", type=Path, default=DEFAULT_DEDUPE_REPORT)
    parser.add_argument("--series-review", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--skip-dedupe", action="store_true")
    args = parser.parse_args()

    vtc_events = load_json_fixture(args.vtc_input)
    second_events = load_json_fixture(args.second_input)

    if not isinstance(vtc_events, list):
        raise TypeError("Visit Tri-Cities fixture must be a list")
    if not isinstance(second_events, list):
        raise TypeError("second source fixture must be a list")

    result = run_pipeline(
        [
            SourceBatch(source_name=VTC_SOURCE_NAME, events=vtc_events),
            SourceBatch(source_name=args.second_source_name, events=second_events),
        ],
        deduplicate=not args.skip_dedupe,
    )

    save_json_fixture(args.publisher_ready, result.publisher_ready_events)
    save_json_fixture(args.deduplicated, result.deduplicated_publisher_ready_events)
    save_json_fixture(args.dedupe_report, result.duplicate_groups)
    save_json_fixture(args.series_review, result.recurrence_review_events)

    print(result.counts)
    print(f"Publisher-ready: {args.publisher_ready}")
    print(f"Deduplicated publisher-ready: {args.deduplicated}")
    print(f"Deduplication report: {args.dedupe_report}")
    print(f"Series review: {args.series_review}")


if __name__ == "__main__":
    main()
