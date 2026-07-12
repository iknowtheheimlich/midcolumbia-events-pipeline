"""Harvest live sources and generate the weekly Reddit artifact.

Attempt_32_LiveProductionPublisher

This command is the production path. It does not read tracked event fixtures.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from adapters.harvest import HarvestOptions, harvest_adapter
from adapters.registry import AVAILABLE_ADAPTERS
from src.pipeline import PipelineResult, SourceBatch, run_pipeline
from src.publisher_editorial import EditorialEvent, auto_publish_events, rejected_events, review_events
from src.reddit_renderer import default_artifact_path, write_reddit_artifact
from src.venue_registry import VenueRegistry

DEFAULT_REGISTRY = Path("generated/venue_registry/registry.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--week-start",
        type=_parse_date,
        required=True,
        help="First included date in YYYY-MM-DD format",
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--months", type=int, default=2)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(AVAILABLE_ADAPTERS),
        help="Limit harvesting to one or more named sources",
    )
    args = parser.parse_args()

    if args.days < 1:
        parser.error("--days must be at least 1")
    if not args.registry.exists():
        parser.error(
            f"venue registry not found: {args.registry}. "
            "Run python -m tools.import_venue_registry first."
        )

    source_names = sorted(args.source or AVAILABLE_ADAPTERS)
    options = HarvestOptions(fetch_raw=True, months=args.months)
    harvest_results = [
        harvest_adapter(AVAILABLE_ADAPTERS[source_name], options)
        for source_name in source_names
    ]

    batches = [
        SourceBatch(source_name=result.source_name, events=result.normalized_events)
        for result in harvest_results
    ]
    registry = VenueRegistry.from_json(args.registry)
    pipeline = run_pipeline(
        batches,
        deduplicate=True,
        venue_registry=registry,
        enrich_geography=True,
        screen_content=True,
    )

    weekly_projection = [
        event
        for event in pipeline.publisher_projection
        if _in_week(event.start_date, args.week_start, args.days)
    ]
    editorial = _weekly_editorial_events(pipeline, args.week_start, args.days)
    publishable = auto_publish_events(editorial)
    review = review_events(editorial)
    rejected = rejected_events(editorial)

    output = args.output or default_artifact_path(args.week_start)
    write_reddit_artifact(publishable, output)

    print(f"Sources: {len(harvest_results)}")
    print(f"Harvested events: {len(pipeline.all_events)}")
    print(f"Content rejected: {len(pipeline.content_rejected_events)}")
    print(f"Deduplicated publisher events: {len(pipeline.deduplicated_publisher_ready_events)}")
    print(f"Weekly events: {len(weekly_projection)}")
    print(f"Auto-published: {len(publishable)}")
    print(f"Review queue: {len(review)}")
    print(f"Rejected: {len(rejected)}")
    print(f"Artifact: {output}")

    warnings = [result for result in harvest_results if result.error]
    for result in warnings:
        print(f"Warning: {result.source_name}: {result.error}")

    return 0


def _weekly_editorial_events(
    pipeline: PipelineResult,
    week_start: date,
    days: int,
) -> list[EditorialEvent]:
    """Return weekly editorial records from the pipeline's valid aggregate property."""
    return [
        event
        for event in pipeline.editorial_projection
        if _in_week(event.start_date, week_start, days)
    ]


def _in_week(value: str, week_start: date, days: int) -> bool:
    try:
        event_date = _parse_date(value)
    except (TypeError, ValueError):
        return False
    return week_start <= event_date < week_start + timedelta(days=days)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


if __name__ == "__main__":
    raise SystemExit(main())
