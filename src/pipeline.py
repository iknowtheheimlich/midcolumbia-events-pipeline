"""Unified source-agnostic pipeline spine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.recurrence_classifier import split_publisher_ready


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

    @property
    def counts(self) -> dict[str, int]:
        """Return simple event counts for smoke tests and logs."""
        return {
            "all_events": len(self.all_events),
            "publisher_ready_events": len(self.publisher_ready_events),
            "recurrence_review_events": len(self.recurrence_review_events),
        }


def run_pipeline(source_batches: list[SourceBatch]) -> PipelineResult:
    """Run normalized source batches through shared pre-publisher stages.

    This is intentionally small. Venue resolution, deduplication, and publishing
    will plug into this spine as separate milestones.
    """
    all_events = combine_source_batches(source_batches)
    publisher_ready, recurrence_review = split_publisher_ready(all_events)

    return PipelineResult(
        all_events=all_events,
        publisher_ready_events=publisher_ready,
        recurrence_review_events=recurrence_review,
    )


def combine_source_batches(source_batches: list[SourceBatch]) -> list[dict[str, Any]]:
    """Combine source batches and preserve source identity on each event."""
    combined: list[dict[str, Any]] = []

    for batch in source_batches:
        for event in batch.events:
            copied = dict(event)
            copied.setdefault("source", batch.source_name)
            combined.append(copied)

    return combined
