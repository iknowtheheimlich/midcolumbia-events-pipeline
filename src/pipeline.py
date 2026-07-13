"""Unified source-agnostic pipeline spine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.category_intelligence import enrich_event_category
from src.content_classifier import screen_events
from src.deduplicate import DeduplicationResult, deduplicate_events
from src.geography import enrich_event_geography
from src.intelligence import attach_intelligence
from src.occurrence_resolution import resolve_occurrences
from src.publisher_editorial import (
    EditorialEvent,
    auto_publish_events,
    community_events,
    main_events,
    prepare_editorial_events,
    rejected_events,
    review_events,
)
from src.publisher_projection import PublisherEvent, project_events
from src.recurrence_classifier import split_publisher_ready
from src.text_normalization import normalize_event
from src.time_semantics import enrich_event_time_semantics
from src.venue_registry import VenueMatch, VenueRegistry


@dataclass(frozen=True)
class SourceBatch:
    """Normalized events emitted by one source adapter."""

    source_name: str
    events: list[dict[str, Any]]


@dataclass(frozen=True)
class PipelineResult:
    """Pipeline output queues."""

    all_events: list[dict[str, Any]] = field(default_factory=list)
    content_rejected_events: list[dict[str, Any]] = field(default_factory=list)
    publisher_ready_events: list[dict[str, Any]] = field(default_factory=list)
    recurrence_review_events: list[dict[str, Any]] = field(default_factory=list)
    deduplicated_publisher_ready_events: list[dict[str, Any]] = field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)
    skipped_low_quality_dedupe: int = 0

    @property
    def counts(self) -> dict[str, int]:
        counts = {
            "all_events": len(self.all_events),
            "publisher_ready_events": len(self.publisher_ready_events),
            "recurrence_review_events": len(self.recurrence_review_events),
            "deduplicated_publisher_ready_events": len(self.deduplicated_publisher_ready_events),
            "duplicate_groups": len(self.duplicate_groups),
            "skipped_low_quality_dedupe": self.skipped_low_quality_dedupe,
        }
        if self.content_rejected_events:
            counts["content_rejected_events"] = len(self.content_rejected_events)
        return counts

    @property
    def publisher_projection(self) -> list[PublisherEvent]:
        return project_events(self.deduplicated_publisher_ready_events)

    @property
    def editorial_projection(self) -> list[EditorialEvent]:
        return prepare_editorial_events(self.publisher_projection)

    @property
    def auto_publish_editorial_events(self) -> list[EditorialEvent]:
        return auto_publish_events(self.editorial_projection)

    @property
    def editorial_review_events(self) -> list[EditorialEvent]:
        return review_events(self.editorial_projection)

    @property
    def editorial_rejected_events(self) -> list[EditorialEvent]:
        return rejected_events(self.editorial_projection)

    @property
    def main_publisher_events(self) -> list[EditorialEvent]:
        return main_events(self.editorial_projection)

    @property
    def community_publisher_events(self) -> list[EditorialEvent]:
        return community_events(self.editorial_projection)


def run_pipeline(
    source_batches: list[SourceBatch],
    *,
    deduplicate: bool = False,
    resolve_cross_source_occurrences: bool = False,
    venue_registry: VenueRegistry | None = None,
    enrich_geography: bool = False,
    screen_content: bool = False,
    enrich_categories: bool = False,
    enrich_time_semantics: bool = False,
) -> PipelineResult:
    """Run source batches through shared enrichment and publisher preparation.

    ``deduplicate`` retains the established conservative exact-key contract.
    ``resolve_cross_source_occurrences`` is an additive identity stage that runs
    after exact deduplication. Production enables both; legacy callers keep their
    historical counts and semantics. Time semantics is likewise opt-in so old
    fixture contracts do not change under existing callers.
    """
    all_events = combine_source_batches(
        source_batches,
        venue_registry=venue_registry,
        enrich_geography=enrich_geography,
        enrich_categories=enrich_categories,
        enrich_time_semantics=enrich_time_semantics,
    )

    content_rejected: list[dict[str, Any]] = []
    publisher_candidates = all_events
    if screen_content:
        publisher_candidates, content_rejected = screen_events(all_events)

    publisher_ready, recurrence_review = split_publisher_ready(publisher_candidates)

    if deduplicate:
        dedupe_result = deduplicate_events(publisher_ready)
    else:
        dedupe_result = DeduplicationResult(events=list(publisher_ready))

    final_events = dedupe_result.events
    duplicate_groups = list(dedupe_result.duplicate_groups)
    if resolve_cross_source_occurrences:
        resolution = resolve_occurrences(final_events)
        final_events = resolution.events
        duplicate_groups.extend(resolution.groups)

    return PipelineResult(
        all_events=all_events,
        content_rejected_events=content_rejected,
        publisher_ready_events=publisher_ready,
        recurrence_review_events=recurrence_review,
        deduplicated_publisher_ready_events=final_events,
        duplicate_groups=duplicate_groups,
        skipped_low_quality_dedupe=dedupe_result.skipped_low_quality,
    )


def combine_source_batches(
    source_batches: list[SourceBatch],
    *,
    venue_registry: VenueRegistry | None = None,
    enrich_geography: bool = False,
    enrich_categories: bool = False,
    enrich_time_semantics: bool = False,
) -> list[dict[str, Any]]:
    """Combine batches and optionally apply shared enrichment layers."""
    combined: list[dict[str, Any]] = []

    for batch in source_batches:
        for event in batch.events:
            copied = normalize_event(event)
            copied.setdefault("source", batch.source_name)
            if enrich_time_semantics:
                copied = enrich_event_time_semantics(copied)
            if venue_registry is not None:
                copied, match = venue_registry.enrich_event(copied)
                copied = _attach_venue_explanation(copied, match)
                if match.status == "matched" and match.record is not None:
                    record = match.record
                    if record.reddit_combo:
                        copied["venue_reddit_combo"] = record.reddit_combo
                    if record.website:
                        copied["venue_website"] = record.website
                    copied["venue_registry_name"] = record.venue_name
            if enrich_geography:
                had_city = bool(str(copied.get("city") or "").strip())
                had_address = bool(str(copied.get("address") or "").strip())
                copied = enrich_event_geography(copied)
                geo_reason = "city_region_lookup" if had_city else "address_city_parse" if had_address else "location_unresolved"
                geo_confidence = 0.98 if had_city else 0.90 if had_address else 0.0
                copied = attach_intelligence(
                    copied,
                    "geographic_scope",
                    copied.get("geo_scope"),
                    geo_confidence,
                    geo_reason,
                )
            if enrich_categories:
                copied = enrich_event_category(copied)
                copied = attach_intelligence(
                    copied,
                    "category",
                    copied.get("category"),
                    float(copied.get("category_confidence") or 0.0),
                    str(copied.get("category_reason") or "no_category_rule_matched"),
                )
            combined.append(copied)

    return combined


def _attach_venue_explanation(event: dict[str, Any], match: VenueMatch) -> dict[str, Any]:
    confidence_by_method = {
        "alias": 1.0,
        "address": 1.0,
        "street_address": 0.98,
        "venue_as_address": 0.98,
        "known_alias": 0.99,
        "parent_room": 0.98,
        "branch_rewrite": 0.97,
        "city_branch": 0.95,
    }
    if match.status == "matched" and match.record is not None:
        return attach_intelligence(
            event,
            "venue",
            match.record.canonical_name,
            confidence_by_method.get(match.method or "", 0.95),
            f"registry_{match.method or 'match'}",
        )
    return attach_intelligence(
        event,
        "venue",
        event.get("venue"),
        0.0,
        f"registry_{match.status}",
    )
