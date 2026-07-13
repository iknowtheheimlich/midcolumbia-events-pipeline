"""Evidence-based resolution of source records describing the same occurrence.

Attempt_43_OccurrenceResolution

The resolver merges provenance, not programs. Separate legitimate sessions remain
separate occurrences for downstream Program Intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Iterable

from adapters.registry import SOURCE_REGISTRY
from src.explainable_intelligence import add_decision
from src.deduplicate import normalize_text


@dataclass(frozen=True)
class OccurrenceEvidence:
    confidence: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class OccurrenceResolutionResult:
    events: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    skipped_low_quality: int = 0


def resolve_occurrences(events: Iterable[dict[str, Any]]) -> OccurrenceResolutionResult:
    """Resolve records into occurrences using conservative independent signals."""
    clusters: list[list[dict[str, Any]]] = []
    skipped = 0

    for event in events:
        if not _minimum_identity(event):
            clusters.append([event])
            skipped += 1
            continue

        matched_index: int | None = None
        matched_evidence: OccurrenceEvidence | None = None
        for index, cluster in enumerate(clusters):
            evidence = compare_occurrences(cluster[0], event)
            if evidence.confidence >= 0.90:
                matched_index = index
                matched_evidence = evidence
                break

        if matched_index is None:
            clusters.append([event])
        else:
            clusters[matched_index].append(event)
            cluster = clusters[matched_index]
            cluster[0] = _merge_cluster(cluster, matched_evidence)
            del cluster[1:]

    output: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for cluster in clusters:
        event = cluster[0]
        output.append(event)
        provenance = event.get("occurrence_provenance") or []
        if len(provenance) > 1:
            decision = (event.get("intelligence") or {}).get("occurrence_resolution") or {}
            groups.append(
                {
                    "canonical_title": event.get("title"),
                    "confidence": decision.get("confidence"),
                    "reason": decision.get("reason"),
                    "source_events": provenance,
                }
            )

    return OccurrenceResolutionResult(events=output, groups=groups, skipped_low_quality=skipped)


def compare_occurrences(left: dict[str, Any], right: dict[str, Any]) -> OccurrenceEvidence:
    """Return explainable evidence that two records describe one occurrence."""
    if normalize_text(left.get("start_date")) != normalize_text(right.get("start_date")):
        return OccurrenceEvidence(0.0, ("different_date",))

    reasons: list[str] = ["same_date"]
    confidence = 0.20

    left_urls = _urls(left)
    right_urls = _urls(right)
    if left_urls & right_urls:
        return OccurrenceEvidence(1.0, ("shared_url", "same_date"))

    left_eventbrite = normalize_text(left.get("eventbrite_event_id"))
    right_eventbrite = normalize_text(right.get("eventbrite_event_id"))
    if left_eventbrite and left_eventbrite == right_eventbrite:
        return OccurrenceEvidence(1.0, ("same_eventbrite_id", "same_date"))

    left_venue = normalize_text(left.get("venue_id") or left.get("venue"))
    right_venue = normalize_text(right.get("venue_id") or right.get("venue"))
    if left_venue and left_venue == right_venue:
        confidence += 0.30
        reasons.append("same_venue")
    else:
        return OccurrenceEvidence(confidence, tuple(reasons + ["different_venue"]))

    time_delta = _time_delta_minutes(left.get("start_time"), right.get("start_time"))
    if time_delta is not None and time_delta <= 10:
        confidence += 0.25
        reasons.append("start_time_within_10m")
    elif time_delta is None:
        reasons.append("missing_start_time")
    else:
        return OccurrenceEvidence(confidence, tuple(reasons + ["different_start_time"]))

    title_score = _title_similarity(left, right)
    if title_score >= 0.90:
        confidence += 0.25
        reasons.append(f"title_similarity={title_score:.2f}")
    elif title_score >= 0.75:
        confidence += 0.18
        reasons.append(f"title_similarity={title_score:.2f}")
    else:
        return OccurrenceEvidence(confidence, tuple(reasons + [f"title_similarity={title_score:.2f}"]))

    return OccurrenceEvidence(min(confidence, 1.0), tuple(reasons))


def _merge_cluster(group: list[dict[str, Any]], evidence: OccurrenceEvidence | None) -> dict[str, Any]:
    primary = max(group, key=_source_priority)
    merged = dict(primary)
    provenance = []
    sources: list[str] = []
    urls: list[str] = []

    for event in group:
        source = str(event.get("source") or "").strip()
        if source and source not in sources:
            sources.append(source)
        for url in _urls(event):
            if url not in urls:
                urls.append(url)
        provenance.extend(event.get("occurrence_provenance") or [_summarize(event)])

    merged["sources"] = sources
    merged["duplicate_sources"] = sources
    merged["source_urls"] = urls
    merged["duplicate_count"] = len(provenance)
    merged["occurrence_provenance"] = provenance
    if evidence:
        add_decision(
            merged,
            "occurrence_resolution",
            merged.get("title"),
            evidence.confidence,
            "+".join(evidence.reasons),
        )
    return merged


def _source_priority(event: dict[str, Any]) -> tuple[int, int]:
    source = str(event.get("source") or "")
    try:
        priority = SOURCE_REGISTRY.get(source).priority
    except KeyError:
        priority = 0
    richness = sum(bool(event.get(field)) for field in ("description", "venue_id", "organization", "external_url"))
    return priority, richness


def _title_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    a = normalize_text(left.get("title"))
    b = normalize_text(right.get("title"))
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _time_delta_minutes(left: Any, right: Any) -> int | None:
    if not left or not right:
        return None
    parsed = []
    for value in (left, right):
        text = str(value).strip()
        item = None
        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p"):
            try:
                item = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if item is None:
            return None
        parsed.append(item.hour * 60 + item.minute)
    return abs(parsed[0] - parsed[1])


def _urls(event: dict[str, Any]) -> set[str]:
    values = [event.get("url"), event.get("external_url"), event.get("eventbrite_url")]
    values.extend(event.get("source_urls") or [])
    return {str(value).strip() for value in values if value and str(value).strip()}


def _minimum_identity(event: dict[str, Any]) -> bool:
    return bool(normalize_text(event.get("title")) and normalize_text(event.get("start_date")))


def _summarize(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": event.get("title"),
        "source": event.get("source"),
        "url": event.get("url"),
        "venue": event.get("venue"),
        "venue_id": event.get("venue_id"),
        "start_date": event.get("start_date"),
        "start_time": event.get("start_time"),
    }
