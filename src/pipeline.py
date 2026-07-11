"""Unified source-agnostic pipeline spine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.deduplicate import DeduplicationResult, deduplicate_events
from src.geography import enrich_event_geography
from src.recurrence_classifier import split_publisher_ready
from src.text_normalization import normalize_event
from src.venue_registry import VenueRegistry


@dataclass(frozen=True)
class SourceBatch:
    """Normalized events emitted by one source adapter."""

    source_name: str
    events: list[dict[str, Any]]


@dataclass(frozen=True)
class PipelineResult:
    """Pipeline output queues."""

    all_events: list[dict[str, Any]] = field(default_factory=list)
    publisher_ready_events: list[dict[str, Any]] = field(default_factory=list)
    recurrence_review_events: list[dict[str, Any]] = field(default_factory=list)
    deduplicated_publisher_ready_events: list[dict[str, Any]] = field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)
    skipped_low_quality_dedupe: int = 0

    @property
    def counts(self) -> dict[str, int]:
        """Return simple event counts for smoke tests and logs."""
        return {
            "all_events": len(self.all_events),
            "publisher_ready_events": len(self.publisher_ready_events),
            "recurrence_review_events": len(self.recurrence_review_events),
            "deduplicated_publisher_ready_events": len(self.deduplicated_publisher_ready_events),
            "duplicate_groups": len(self.duplicate_groups),
            "skipped_low_quality_dedupe": self.skipped_low_quality_dedupe,
        }


def run_pipeline(
    source_batches: list[SourceBatch],
    *,
    deduplicate: bool = False,
    venue_registry: VenueRegistry | None = None,
    enrich_geography: bool = False,
) -> PipelineResult:
    """Run normalized source batches through shared pre-publisher stages."""
    all_events = combine_source_batches(
        source_batches,
        venue_registry=venue_registry,
        enrich_geography=enrich_geography,
    )
    publisher_ready, recurrence_review = split_publisher_ready(all_events)

    if deduplicate:
        dedupe_result = deduplicate_events(publisher_ready)
    else:
        dedupe_result = DeduplicationResult(events=list(publisher_ready))

    return PipelineResult(
        all_events=all_events,
        publisher_ready_events=publisher_ready,
        recurrence_review_events=recurrence_review,
        deduplicated_publisher_ready_events=dedupe_result.events,
        duplicate_groups=dedupe_result.duplicate_groups,
        skipped_low_quality_dedupe=dedupe_result.skipped_low_quality,
    )


def combine_source_batches(
    source_batches: list[SourceBatch],
    *,
    venue_registry: VenueRegistry | None = None,
    enrich_geography: bool = False,
) -> list[dict[str, Any]]:
    """Combine batches and optionally enrich venue and geographic intelligence."""
    combined: list[dict[str, Any]] = []

    for batch in source_batches:
        for event in batch.events:
            copied = normalize_event(event)
            copied.setdefault("source", batch.source_name)
            if venue_registry is not None:
                copied, _ = venue_registry.enrich_event(copied)
            if enrich_geography:
                copied = enrich_event_geography(copied)
            combined.append(copied)

    return combined
