"""Evidence-based resolution of source records describing the same occurrence.

Attempt_43_OccurrenceResolution
Attempt_49_OccurrenceResolutionTuning
Attempt_52_SourceLineage

The resolver merges provenance, not programs. Separate legitimate sessions remain
separate occurrences for downstream Program Intelligence. Discovery sources and origin
sources are tracked separately so syndicated copies do not masquerade as corroboration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
import re
from typing import Any, Iterable

from adapters.registry import SOURCE_REGISTRY
from src.explainable_intelligence import add_decision
from src.deduplicate import normalize_text
from src.source_lineage import enrich_event_source_lineage

_WORD_RE = re.compile(r"[a-z0-9]+")
_PROMOTIONAL_WORDS = {"live", "featuring", "presents", "presenting", "hosted", "normal"}
_VENUE_NOISE = {
    "the", "and", "estate", "vineyards", "vineyard", "winery", "cellars",
    "distillery", "tasting", "room", "cocktail", "lounge", "bar", "grill",
    "company", "co",
}


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

    for raw_event in events:
        event = enrich_event_source_lineage(raw_event)
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
                    "discovery_sources": event.get("discovery_sources") or [],
                    "origin_sources": event.get("origin_sources") or [],
                    "independent_source_count": event.get("independent_source_count", 1),
                }
            )

    return OccurrenceResolutionResult(events=output, groups=groups, skipped_low_quality=skipped)


def compare_occurrences(left: dict[str, Any], right: dict[str, Any]) -> OccurrenceEvidence:
    """Return explainable evidence that two records describe one occurrence."""
    if normalize_text(left.get("start_date")) != normalize_text(right.get("start_date")):
        return OccurrenceEvidence(0.0, ("different_date",))

    reasons: list[str] = ["same_date"]
    confidence = 0.20

    if _urls(left) & _urls(right):
        return OccurrenceEvidence(1.0, ("shared_url", "same_date"))

    left_eventbrite = normalize_text(left.get("eventbrite_event_id"))
    right_eventbrite = normalize_text(right.get("eventbrite_event_id"))
    if left_eventbrite and left_eventbrite == right_eventbrite:
        return OccurrenceEvidence(1.0, ("same_eventbrite_id", "same_date"))

    venue_match = _venue_match_reason(left, right)
    if venue_match:
        confidence += 0.32
        reasons.append(venue_match)
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

    title_score, title_reason = _title_similarity(left, right)
    if title_score >= 0.92:
        confidence += 0.28
        reasons.append(f"{title_reason}={title_score:.2f}")
    elif title_score >= 0.80:
        confidence += 0.22
        reasons.append(f"{title_reason}={title_score:.2f}")
    elif title_score >= 0.70 and time_delta is not None and time_delta <= 10:
        confidence += 0.18
        reasons.append(f"{title_reason}={title_score:.2f}")
    else:
        return OccurrenceEvidence(confidence, tuple(reasons + [f"{title_reason}={title_score:.2f}"]))

    return OccurrenceEvidence(min(confidence, 1.0), tuple(reasons))


def _merge_cluster(group: list[dict[str, Any]], evidence: OccurrenceEvidence | None) -> dict[str, Any]:
    primary = max(group, key=_source_priority)
    merged = dict(primary)
    provenance: list[dict[str, Any]] = []
    discovery_sources: list[str] = []
    origin_sources: list[str] = []
    urls: list[str] = []

    for event in group:
        discovery = str(event.get("discovery_source") or event.get("source") or "").strip()
        origin = str(event.get("origin_source") or discovery).strip()
        if discovery and discovery not in discovery_sources:
            discovery_sources.append(discovery)
        if origin and origin not in origin_sources:
            origin_sources.append(origin)
        for url in sorted(_urls(event)):
            if url not in urls:
                urls.append(url)
        provenance.extend(event.get("occurrence_provenance") or [_summarize(event)])

    merged["sources"] = discovery_sources
    merged["duplicate_sources"] = discovery_sources
    merged["discovery_sources"] = discovery_sources
    merged["origin_sources"] = origin_sources
    merged["corroborating_sources"] = origin_sources
    merged["independent_source_count"] = len(origin_sources)
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


def _source_priority(event: dict[str, Any]) -> tuple[int, int, int]:
    discovery = str(event.get("discovery_source") or event.get("source") or "")
    origin = str(event.get("origin_source") or discovery)
    try:
        priority = SOURCE_REGISTRY.get(discovery).priority
    except KeyError:
        priority = 0
    native_origin = int(bool(discovery and origin and discovery == origin))
    richness = sum(bool(event.get(field)) for field in ("description", "venue_id", "organization", "external_url"))
    return native_origin, priority, richness


def _title_similarity(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, str]:
    raw_a = normalize_text(left.get("title"))
    raw_b = normalize_text(right.get("title"))
    if not raw_a or not raw_b:
        return 0.0, "title_similarity"
    if raw_a == raw_b:
        return 1.0, "exact_title"

    a = _identity_title(raw_a, left)
    b = _identity_title(raw_b, right)
    if a == b:
        return 1.0, "normalized_title"

    sequence = SequenceMatcher(None, a, b).ratio()
    token_score = _token_similarity(a, b)
    score = max(sequence, token_score)
    reason = "title_token_similarity" if token_score >= sequence else "title_similarity"
    return score, reason


def _identity_title(value: str, event: dict[str, Any]) -> str:
    text = value.casefold()
    text = re.sub(r"\b(?:live|normal)\b", " ", text)
    text = re.sub(r"\bhosted\s+by\b", " ", text)
    text = re.sub(r"\b(?:at|@)\s+.+$", " ", text)

    venue_phrases = {
        normalize_text(event.get(field))
        for field in ("venue", "venue_registry_name", "parent_venue", "venue_parent")
    }
    for venue in sorted((item for item in venue_phrases if item), key=len, reverse=True):
        text = re.sub(rf"\b(?:at|@)\s+{re.escape(venue.casefold())}\b.*$", " ", text)

    words = [word for word in _WORD_RE.findall(text) if word not in _PROMOTIONAL_WORDS]
    return " ".join(words)


def _token_similarity(left: str, right: str) -> float:
    a = set(_WORD_RE.findall(left))
    b = set(_WORD_RE.findall(right))
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    containment = overlap / min(len(a), len(b))
    jaccard = overlap / len(a | b)
    return max(jaccard, containment * 0.96)


def _venue_match_reason(left: dict[str, Any], right: dict[str, Any]) -> str | None:
    if _venue_ids(left) & _venue_ids(right):
        return "same_venue_id"
    if _venue_names(left) & _venue_names(right):
        return "same_canonical_venue"
    return None


def _venue_ids(event: dict[str, Any]) -> set[str]:
    fields = ("venue_id", "parent_venue_id", "venue_parent_id")
    return {normalize_text(event.get(field)) for field in fields if normalize_text(event.get(field))}


def _venue_names(event: dict[str, Any]) -> set[str]:
    fields = ("venue_registry_name", "venue", "parent_venue", "venue_parent", "organization")
    names: set[str] = set()
    for field in fields:
        value = normalize_text(event.get(field))
        if value:
            normalized = _normalize_venue_name(value)
            if normalized:
                names.add(normalized)
    return names


def _normalize_venue_name(value: str) -> str:
    return " ".join(word for word in _WORD_RE.findall(value.casefold()) if word not in _VENUE_NOISE)


def _time_delta_minutes(left: Any, right: Any) -> int | None:
    if not left or not right:
        return None
    parsed: list[int] = []
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
        "origin_source": event.get("origin_source"),
        "discovery_source": event.get("discovery_source"),
        "is_syndicated": event.get("is_syndicated", False),
        "url": event.get("url"),
        "venue": event.get("venue"),
        "venue_id": event.get("venue_id"),
        "start_date": event.get("start_date"),
        "start_time": event.get("start_time"),
    }
