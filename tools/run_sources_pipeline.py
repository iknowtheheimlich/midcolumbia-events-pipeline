"""Run any number of normalized source fixtures through the unified pipeline.

Usage:
    python -m tools.run_sources_pipeline --source Name=path/to/events.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from src.pipeline import SourceBatch, run_pipeline

DEFAULT_OUTPUT_DIR = Path("fixtures/combined")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run normalized source fixtures through the unified pipeline")
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        help="Source fixture in Name=path format. Repeat for multiple sources.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-dedupe", action="store_true")
    args = parser.parse_args()

    batches = [load_source_batch(spec) for spec in args.source]
    result = run_pipeline(batches, deduplicate=not args.skip_dedupe)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    publisher_ready = args.output_dir / "publisher_ready_events.json"
    deduplicated = args.output_dir / "deduplicated_publisher_ready_events.json"
    review = args.output_dir / "series_review_queue.json"
    report = args.output_dir / "deduplication_report.json"

    save_json_fixture(publisher_ready, result.publisher_ready_events)
    save_json_fixture(deduplicated, result.deduplicated_publisher_ready_events)
    save_json_fixture(review, result.recurrence_review_events)
    save_json_fixture(report, result.duplicate_groups)

    print(result.counts)
    print(f"Publisher-ready: {publisher_ready}")
    print(f"Deduplicated publisher-ready: {deduplicated}")
    print(f"Series review: {review}")
    print(f"Deduplication report: {report}")


def load_source_batch(spec: str) -> SourceBatch:
    source_name, fixture_path = parse_source_spec(spec)
    events = load_json_fixture(fixture_path)
    if not isinstance(events, list):
        raise TypeError(f"source fixture must be a list: {fixture_path}")
    return SourceBatch(source_name=source_name, events=events)


def parse_source_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise ValueError("source must be in Name=path format")
    name, path_text = spec.split("=", 1)
    name = name.strip()
    path_text = path_text.strip()
    if not name or not path_text:
        raise ValueError("source name and path are required")
    return name, Path(path_text)


if __name__ == "__main__":
    main()
