"""Harvest enabled sources and generate dual weekly Reddit artifacts.

This command is the production path. It does not read tracked event fixtures except
where an enabled migration bridge explicitly defines that behavior.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from time import perf_counter

from adapters.harvest import HarvestOptions, harvest_adapter
from adapters.registry import SOURCE_REGISTRY
from src.completeness_audit import DEFAULT_COMPLETENESS_AUDIT_PATH, write_completeness_audit
from src.harvest_health import assess_harvest_health, degraded_artifact_path
from src.harvest_telemetry import (
    DEFAULT_HARVEST_TELEMETRY_PATH,
    append_harvest_telemetry,
    build_harvest_telemetry_records,
)
from src.pipeline import PipelineResult, SourceBatch, run_pipeline
from src.pipeline_inspector import DEFAULT_INSPECTOR_PATH, write_pipeline_inspector
from src.program_intelligence import group_editorial_programs
from src.publisher_audit import default_audit_path, write_publisher_audit
from src.publisher_editorial import EditorialEvent, community_events, main_events, rejected_events, review_events
from src.publishing_contract import PublishingProfile
from src.reddit_renderer import default_community_artifact_path, default_main_artifact_path, render_program_line, write_reddit_artifact
from src.review_trainer import DEFAULT_REVIEW_TRAINING_PATH, write_review_training_artifact
from src.source_attribution import build_source_attribution
from src.source_metrics import DEFAULT_SOURCE_METRICS_PATH, build_source_metrics, write_source_metrics
from src.supplemental_detail_audit import DEFAULT_SUPPLEMENTAL_DETAIL_PATH, write_supplemental_detail_audit
from src.venue_registry import VenueRegistry

DEFAULT_REGISTRY = Path("generated/venue_registry/registry.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week-start", type=_parse_date, required=True, help="First included date in YYYY-MM-DD format")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--months", type=int, default=2)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, help="Legacy alias for --output-main")
    parser.add_argument("--output-main", type=Path)
    parser.add_argument("--output-community", type=Path)
    parser.add_argument("--output-audit", type=Path)
    parser.add_argument("--output-source-metrics", type=Path)
    parser.add_argument("--output-review-training", type=Path)
    parser.add_argument("--output-harvest-telemetry", type=Path)
    parser.add_argument("--output-supplemental-details", type=Path)
    parser.add_argument("--output-completeness-audit", type=Path)
    parser.add_argument("--review-corrections", type=Path, help="Optional curated JSON corrections keyed by review fingerprint")
    parser.add_argument("--allow-degraded", action="store_true", help="Permit normal artifact paths despite failed live-source coverage")
    parser.add_argument("--inspect-title", help="Write an HTML trace for records containing this title or text")
    parser.add_argument("--output-inspector", type=Path)
    parser.add_argument("--source", action="append", choices=SOURCE_REGISTRY.names(), help="Limit harvesting to configured source names")
    args = parser.parse_args()

    if args.days < 1:
        parser.error("--days must be at least 1")
    if args.output and args.output_main:
        parser.error("use either --output or --output-main, not both")
    if args.output_inspector and not args.inspect_title:
        parser.error("--output-inspector requires --inspect-title")
    if args.review_corrections and not args.review_corrections.exists():
        parser.error(f"review corrections not found: {args.review_corrections}")
    if not args.registry.exists():
        parser.error(f"venue registry not found: {args.registry}. Run python -m tools.import_venue_registry first.")

    selected_adapters = [SOURCE_REGISTRY.get(name) for name in args.source] if args.source else SOURCE_REGISTRY.enabled()
    source_names = [adapter.source_name for adapter in selected_adapters]
    publication_footnote = build_source_attribution(selected_adapters)
    options = HarvestOptions(fetch_raw=True, months=args.months)
    harvest_results = []
    harvest_durations_ms: dict[str, int] = {}
    for adapter in selected_adapters:
        started = perf_counter()
        result = harvest_adapter(adapter, options)
        harvest_durations_ms[result.source_name] = round((perf_counter() - started) * 1000)
        harvest_results.append(result)

    health = assess_harvest_health(selected_adapters, harvest_results)
    telemetry_output = args.output_harvest_telemetry or DEFAULT_HARVEST_TELEMETRY_PATH
    append_harvest_telemetry(
        build_harvest_telemetry_records(health, harvest_results, harvest_durations_ms),
        telemetry_output,
    )
    blocked = health.degraded and not args.allow_degraded

    batches = [SourceBatch(source_name=result.source_name, events=result.normalized_events) for result in harvest_results]
    pipeline = run_pipeline(
        batches,
        deduplicate=True,
        resolve_cross_source_occurrences=True,
        venue_registry=VenueRegistry.from_json(args.registry),
        enrich_geography=True,
        screen_content=True,
        enrich_categories=True,
        enrich_time_semantics=True,
    )

    weekly_projection = [event for event in pipeline.publisher_projection if _in_week(event.start_date, args.week_start, args.days)]
    editorial = _weekly_editorial_events(pipeline, args.week_start, args.days)
    main_publishable = main_events(editorial)
    community_publishable = community_events(editorial)
    main_programs = group_editorial_programs(main_publishable)
    community_programs = group_editorial_programs(community_publishable)
    review = review_events(editorial)
    rejected = rejected_events(editorial)
    profile = PublishingProfile.load()

    main_output = args.output_main or args.output or default_main_artifact_path()
    community_output = args.output_community or default_community_artifact_path()
    audit_output = args.output_audit or default_audit_path()
    metrics_output = args.output_source_metrics or DEFAULT_SOURCE_METRICS_PATH
    review_training_output = args.output_review_training or DEFAULT_REVIEW_TRAINING_PATH
    supplemental_output = args.output_supplemental_details or DEFAULT_SUPPLEMENTAL_DETAIL_PATH
    completeness_output = args.output_completeness_audit or DEFAULT_COMPLETENESS_AUDIT_PATH
    if blocked:
        main_output = degraded_artifact_path(main_output)
        community_output = degraded_artifact_path(community_output)
        audit_output = degraded_artifact_path(audit_output)
        metrics_output = degraded_artifact_path(metrics_output)
        supplemental_output = degraded_artifact_path(supplemental_output)
        completeness_output = degraded_artifact_path(completeness_output)

    write_reddit_artifact(main_programs, main_output, footnote=publication_footnote, category_order=profile.category_order)
    write_reddit_artifact(community_programs, community_output, footnote=publication_footnote, category_order=profile.category_order)
    write_publisher_audit(editorial, audit_output, category_order=profile.category_order)
    write_supplemental_detail_audit(pipeline.all_events, supplemental_output, week_start=args.week_start, days=args.days)
    write_completeness_audit(
        pipeline.deduplicated_publisher_ready_events,
        completeness_output,
        week_start=args.week_start,
        days=args.days,
    )

    source_metrics = build_source_metrics(
        selected_adapters,
        harvest_results,
        content_rejected_events=pipeline.content_rejected_events,
        duplicate_groups=pipeline.duplicate_groups,
        editorial_events=editorial,
    )
    write_source_metrics(source_metrics, metrics_output)

    if not blocked:
        write_review_training_artifact(review, review_training_output, corrections_path=args.review_corrections)

    inspector_output: Path | None = None
    if args.inspect_title:
        inspector_output = args.output_inspector or DEFAULT_INSPECTOR_PATH
        if blocked:
            inspector_output = degraded_artifact_path(inspector_output)
        collected = [event for result in harvest_results for event in result.normalized_events]
        programs = [*main_programs, *community_programs]
        write_pipeline_inspector(
            args.inspect_title,
            {
                "Collected source records": collected,
                "Normalized and enriched events": pipeline.all_events,
                "Publisher-ready occurrences": pipeline.publisher_ready_events,
                "Resolved occurrences": pipeline.deduplicated_publisher_ready_events,
                "Publisher projection": weekly_projection,
                "Editorial projection": editorial,
                "Program projection": programs,
            },
            inspector_output,
            rendered_lines=[render_program_line(program) for program in programs],
        )

    print(f"Production status: {health.status}{' (override)' if health.degraded and args.allow_degraded else ''}")
    for item in health.failed_required_sources:
        print(f"  {item.source_name}: {item.status} - {item.reason or 'live coverage unavailable'}")
    print(f"Sources: {len(harvest_results)} ({', '.join(source_names)})")
    print(f"Harvested events: {len(pipeline.all_events)}")
    print(f"Content rejected: {len(pipeline.content_rejected_events)}")
    print(f"Deduplicated publisher events: {len(pipeline.deduplicated_publisher_ready_events)}")
    print(f"Weekly events: {len(weekly_projection)}")
    print(f"Main events: {len(main_publishable)} -> {len(main_programs)} programs")
    print(f"Community events: {len(community_publishable)} -> {len(community_programs)} programs")
    print(f"Review queue: {len(review)}")
    print(f"Rejected: {len(rejected)}")
    print(f"Main artifact: {main_output}")
    print(f"Community artifact: {community_output}")
    print(f"Audit artifact: {audit_output}")
    print(f"Supplemental details: {supplemental_output}")
    print(f"Completeness audit: {completeness_output}")
    print(f"Source metrics: {metrics_output}")
    print(f"Harvest telemetry: {telemetry_output}")
    if blocked:
        print("Review training: skipped (degraded harvest)")
    else:
        print(f"Review training: {review_training_output}")
    if inspector_output is not None:
        print(f"Pipeline inspector: {inspector_output}")
    for result in harvest_results:
        if result.error:
            print(f"Warning: {result.source_name}: {result.error}")
    return 2 if blocked else 0


def _weekly_editorial_events(pipeline: PipelineResult, week_start: date, days: int) -> list[EditorialEvent]:
    return [event for event in pipeline.editorial_projection if _in_week(event.start_date, week_start, days)]


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
