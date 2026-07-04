"""Conservative multi-source event deduplication."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DeduplicationResult:
    """Deduplicated events and merge report."""

    events: list[dict[str, Any]] = field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        """Return before/after style counts."""
        duplicate_count = sum(max(0, len(group.get("source_events", [])) - 1) for group in self.duplicate_groups)
        return {
            "deduplicated_events": len(self.events),
            "duplicate_groups": len(self.duplicate_groups),
            "duplicate_events_removed": duplicate_count,
        }


def deduplicate_events(events: list[dict[str, Any]]) -> DeduplicationResult:
    """Deduplicate publisher-ready events using conservative exact keys."""
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}

    for event in events:
        key = dedupe_key(event)
        grouped.setdefault(key, []).append(event)

    output_events: list[dict[str, Any]] = []
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
                "source_events": [summarize_source_event(event) for event in group],
            }
        )

    return DeduplicationResult(events=output_events, duplicate_groups=duplicate_groups)


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


def merge_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge exact-key duplicate events while preserving provenance."""
    primary = dict(group[0])
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
    }


def normalize_text(value: Any) -> str:
    """Normalize text for exact-key matching."""
    if value is None:
        return ""
    text = str(value).casefold().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
