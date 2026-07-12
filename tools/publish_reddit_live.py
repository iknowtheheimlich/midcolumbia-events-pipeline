"""Harvest enabled sources and generate dual weekly Reddit artifacts.

Attempt_32_LiveProductionPublisher
Attempt_35_DualPublisher
Attempt_36_SourceRegistry

This command is the production path. It does not read tracked event fixtures
except where an enabled migration bridge explicitly defines that behavior.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from adapters.harvest import HarvestOptions, harvest_adapter
from adapters.registry import SOURCE_REGISTRY
from src.pipeline import PipelineResult, SourceBatch, run_pipeline
from src.publisher_audit import default_audit_path, write_publisher_audit
from src.publisher_editorial import (
    EditorialEvent,
    community_events,
    main_events,
    rejected_events,
    review_events,
)
from src.publishing_contract import PublishingProfile
from src.reddit_renderer import (
    default_community_artifact_path,
    default_main_artifact_path,
    write_reddit_artifact,
)
from src.source_metrics import (
    DEFAULT_SOURCE_METRICS_PATH,
    build_source_metrics,
    write_source_metrics,
)
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
    parser.add_argument("--output", type=Path, help="Legacy alias for --output-main")
    parser.add_argument("--output-main", type=Path)
    parser.add_argument("--output-community", type=Path)
    parser.add_argument("--output-audit", type=Path)
    parser.add_argument("--output-source-metrics", type=Path)
    parser.add_argument(
        "--source",
        action="append",
        choices=SOURCE_REGISTRY.names(),
        help="Limit harvesting to configured source names, including disabled sources",
    )
    args = parser.parse_args()

    if args.days < 1:
        parser.error("--days must be at least 1")
    if args.output and args.output_main:
        parser.error("use either --output or --output-main, not both")
    if not args.registry.exists():
        parser.error(
            f"venue registry not found: {args.registry}. "
            "Run python -m tools.import_venue_registry first."
        )

    selected_adapters = (
        [SOURCE_REGISTRY.get(name) for name in args.source]
        if args.source
        else SOURCE_REGISTRY.enabled()
    )
    source_names = [adapter.source_name for adapter in selected_adapters]
    options = HarvestOptions(fetch_raw=True, months=args.months)
    harvest_results = [harvest_adapter(adapter, options) for adapter in selected_adapters]

    batches = [
        SourceBatch(source_name=result.source_name, events=result.normalized_events)
        for result in harvest_results
    ]
    venue_registry = VenueRegistry.from_json(args.registry)
    pipeline = run_pipeline(
        batches,
        deduplicate=True,
        venue_registry=venue_registry,
        enrich_geography=True,
        screen_content=True,
    )

    weekly_projection = [
        event
        for event in pipeline.publisher_projection
        if _in_week(event.start_date, args.week_start, args.days)
    ]
    editorial = _weekly_editorial_events(pipeline, args.week_start, args.days)
    main_publishable = main_events(editorial)
    community_publishable = community_events(editorial)
    review = review_events(editorial)
    rejected = rejected_events(editorial)
    profile = PublishingProfile.load()

    main_output = args.output_main or args.output or default_main_artifact_path()
    community_output = args.output_community or default_community_artifact_path()
    audit_output = args.output_audit or default_audit_path()
    metrics_output = args.output_source_metrics or DEFAULT_SOURCE_METRICS_PATH

    write_reddit_artifact(
        main_publishable,
        main_output,
        category_order=profile.category_order,
    )
    write_reddit_artifact(
        community_publishable,
        community_output,
        category_order=profile.category_order,
    )
    write_publisher_audit(
        editorial,
        audit_output,
        category_order=profile.category_order,
    )

    source_metrics = build_source_metrics(
        selected_adapters,
        harvest_results,
        content_rejected_events=pipeline.content_rejected_events,
        duplicate_groups=pipeline.duplicate_groups,
        editorial_events=editorial,
    )
    write_source_metrics(source_metrics, metrics_output)

    print(f"Sources: {len(harvest_results)} ({', '.join(source_names)})")
    print(f"Harvested events: {len(pipeline.all_events)}")
    print(f"Content rejected: {len(pipeline.content_rejected_events)}")
    print(f"Deduplicated publisher events: {len(pipeline.deduplicated_publisher_ready_events)}")
    print(f"Weekly events: {len(weekly_projection)}")
    print(f"Main events: {len(main_publishable)}")
    print(f"Community events: {len(community_publishable)}")
    print(f"Review queue: {len(review)}")
    print(f"Rejected: {len(rejected)}")
    print(f"Main artifact: {main_output}")
    print(f"Community artifact: {community_output}")
    print(f"Audit artifact: {audit_output}")
    print(f"Source metrics: {metrics_output}")

    for result in harvest_results:
        if result.error:
            print(f"Warning: {result.source_name}: {result.error}")

    return 0


def _weekly_editorial_events(
    pipeline: PipelineResult,
    week_start: date,
    days: int,
) -> list[EditorialEvent]:
    """Return weekly editorial records from the pipeline aggregate property."""
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
