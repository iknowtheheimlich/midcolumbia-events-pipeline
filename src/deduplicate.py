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

    output_events, semantic_groups = _merge_semantic_duplicates(output_events)
    duplicate_groups.extend(semantic_groups)

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
    primary["dedupe_provenance"] = [summarize_source_event(event) for event in group]
    venue_source = _best_supported_venue(group)
    if venue_source is not None:
        for field in ("venue", "venue_id", "venue_registry_name", "display_venue", "display_url", "display_city"):
            if venue_source.get(field) not in (None, ""):
                primary[field] = venue_source[field]
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
        "end_time": event.get("end_time"),
        "source_event_id": event.get("source_event_id"),
        "completeness_percent": event.get("completeness_percent"),
        "publication_blocker_reason": event.get("publication_blocker_reason"),
        "captain_state": event.get("captain_state"),
    }


def _canonical_rank(event: dict[str, Any]) -> tuple[int, float, int, int]:
    completeness, populated = completeness_rank(event)
    source = str(event.get("source") or "")
    try:
        priority = SOURCE_REGISTRY.get(source).priority
    except KeyError:
        priority = 0
    unblocked = int(not bool(event.get("publication_blocker_reason")))
    return unblocked, completeness, priority, populated


def normalize_text(value: Any) -> str:
    """Normalize text for exact-key matching."""
    if value is None:
        return ""
    text = str(value).casefold().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _merge_semantic_duplicates(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge only cross-source occurrences with multiple independent agreements."""
    parent = list(range(len(events)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    for left, first in enumerate(events):
        for right in range(left + 1, len(events)):
            second = events[right]
            if _semantic_duplicate(first, second):
                union(left, right)

    groups: dict[int, list[dict[str, Any]]] = {}
    for index, event in enumerate(events):
        groups.setdefault(find(index), []).append(event)
    output: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for group in groups.values():
        if len(group) == 1:
            output.append(group[0])
            continue
        merged = merge_group(group)
        output.append(merged)
        audits.append({
            "dedupe_key": "semantic_occurrence",
            "canonical_title": merged.get("title"),
            "canonical_source": merged.get("source"),
            "canonical_completeness": merged.get("completeness_percent"),
            "reason": "same_date+same_start+same_city+semantic_title+venue_or_content_support",
            "source_events": [summarize_source_event(event) for event in group],
        })
    return output, audits


def _semantic_duplicate(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if normalize_text(first.get("source")) == normalize_text(second.get("source")):
        return False
    for field in ("start_date", "start_time", "city"):
        if not normalize_text(first.get(field)) or normalize_text(first.get(field)) != normalize_text(second.get(field)):
            return False
    title_score = _jaccard(first.get("title"), second.get("title"))
    if title_score < 0.50 or len(_distinctive_title_tokens(first.get("title")) & _distinctive_title_tokens(second.get("title"))) < 2:
        return False
    venue_score = _jaccard(
        first.get("venue_id") or first.get("venue_registry_name") or first.get("venue"),
        second.get("venue_id") or second.get("venue_registry_name") or second.get("venue"),
    )
    description_score = _jaccard(first.get("description"), second.get("description"))
    venue_cross_support = (
        _token_subset(first.get("venue"), second.get("description"))
        or _token_subset(second.get("venue"), first.get("description"))
    )
    return venue_score >= 0.40 or description_score >= 0.45 or title_score >= 0.82 or venue_cross_support


def _jaccard(left: Any, right: Any) -> float:
    a, b = set(normalize_text(left).split()), set(normalize_text(right).split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _token_subset(needle: Any, haystack: Any) -> bool:
    wanted = set(normalize_text(needle).split())
    available = set(normalize_text(haystack).split())
    return len(wanted) >= 2 and wanted <= available


def _distinctive_title_tokens(value: Any) -> set[str]:
    generic = {"a", "an", "the", "at", "in", "on", "with", "live", "music", "event", "show", "series"}
    return {token for token in normalize_text(value).split() if len(token) > 1 and token not in generic}


def _best_supported_venue(group: list[dict[str, Any]]) -> dict[str, Any] | None:
    evidence = normalize_text(" ".join(
        str(event.get(field) or "")
        for event in group for field in ("title", "description", "url")
    ))
    evidence_tokens = set(evidence.split())
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for event in group:
        venue_tokens = set(normalize_text(event.get("venue_registry_name") or event.get("venue")).split())
        if not venue_tokens:
            continue
        ranked.append((len(venue_tokens & evidence_tokens), len(venue_tokens), event))
    if not ranked:
        return None
    winner = max(ranked, key=lambda item: (item[0], item[1]))
    return winner[2] if winner[0] else None
