"""Conservative multi-source event deduplication."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from adapters.registry import SOURCE_REGISTRY
from src.event_completeness import completeness_rank


@dataclass(frozen=True)
class DeduplicationResult:
    """Deduplicated events and merge report."""

    events: list[dict[str, Any]] = field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)
    skipped_low_quality: int = 0

    @property
    def counts(self) -> dict[str, int]:
        duplicate_count = sum(max(0, len(group.get("source_events", [])) - 1) for group in self.duplicate_groups)
        return {
            "deduplicated_events": len(self.events),
            "duplicate_groups": len(self.duplicate_groups),
            "duplicate_events_removed": duplicate_count,
            "skipped_low_quality": self.skipped_low_quality,
        }


def deduplicate_events(events: list[dict[str, Any]]) -> DeduplicationResult:
    """Deduplicate publisher-ready events using conservative exact keys.

    Low-quality keys are never grouped. This prevents blank legacy fields from
    collapsing unrelated events into false duplicates.
    """
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    passthrough_events: list[dict[str, Any]] = []
    skipped_low_quality = 0

    for event in events:
        key = dedupe_key(event)
        if not is_high_quality_key(event):
            passthrough_events.append(event)
            skipped_low_quality += 1
            continue
        grouped.setdefault(key, []).append(event)

    output_events: list[dict[str, Any]] = list(passthrough_events)
    duplicate_groups: list[dict[str, Any]] = []

    for key, group in grouped.items():
        if len(group) == 1:
            output_events.append(group[0])
            continue

        merged = merge_group(group)
        output_events.append(merged)
        duplicate_groups.append(
            {
                "dedupe_key": "|".join(key),
                "canonical_title": merged.get("title"),
                "canonical_source": merged.get("source"),
                "canonical_completeness": merged.get("completeness_percent"),
                "source_events": [summarize_source_event(event) for event in group],
            }
        )

    return DeduplicationResult(
        events=output_events,
        duplicate_groups=duplicate_groups,
        skipped_low_quality=skipped_low_quality,
    )


def dedupe_key(event: dict[str, Any]) -> tuple[str, ...]:
    """Build a conservative dedupe key."""
    return (
        normalize_text(event.get("title")),
        normalize_text(event.get("event_kind") or "single"),
        normalize_text(event.get("start_date")),
        normalize_text(event.get("start_time")),
        normalize_text(event.get("city")),
        normalize_text(event.get("venue_id") or event.get("venue")),
    )


def is_high_quality_key(event: dict[str, Any]) -> bool:
    """Return true only when an event has enough fields for safe dedupe."""
    title = normalize_text(event.get("title"))
    start_date = normalize_text(event.get("start_date"))
    start_time = normalize_text(event.get("start_time"))
    city = normalize_text(event.get("city"))
    venue = normalize_text(event.get("venue_id") or event.get("venue"))

    if not title or not start_date:
        return False

    supporting_fields = sum(bool(value) for value in (start_time, city, venue))
    return supporting_fields >= 2


def merge_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge exact-key duplicates while preserving provenance and best record."""
    primary = dict(max(group, key=_canonical_rank))
    sources = []
    urls = []

    for event in group:
        source = event.get("source")
        url = event.get("url")
        if source and source not in sources:
            sources.append(source)
        if url and url not in urls:
            urls.append(url)

    primary["sources"] = sources
    primary["source_urls"] = urls
    primary["duplicate_count"] = len(group)
    return primary


def summarize_source_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return compact duplicate report data for one event."""
    return {
        "title": event.get("title"),
        "source": event.get("source"),
        "url": event.get("url"),
        "venue": event.get("venue"),
        "start_date": event.get("start_date"),
        "start_time": event.get("start_time"),
        "completeness_percent": event.get("completeness_percent"),
    }


def _canonical_rank(event: dict[str, Any]) -> tuple[float, int, int]:
    completeness, populated = completeness_rank(event)
    source = str(event.get("source") or "")
    try:
        priority = SOURCE_REGISTRY.get(source).priority
    except KeyError:
        priority = 0
    return completeness, priority, populated


def normalize_text(value: Any) -> str:
    """Normalize text for exact-key matching."""
    if value is None:
        return ""
    text = str(value).casefold().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
