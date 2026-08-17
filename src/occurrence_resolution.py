"""Evidence-based resolution of source records describing the same occurrence.

Attempt_43_OccurrenceResolution
Attempt_49_OccurrenceResolutionTuning

The resolver merges provenance, not programs. Separate legitimate sessions remain
separate occurrences for downstream Program Intelligence.
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


_WORD_RE = re.compile(r"[a-z0-9]+")
_PROMOTIONAL_WORDS = {
    "live",
    "featuring",
    "presents",
    "presenting",
    "hosted",
    "normal",
}
_VENUE_NOISE = {
    "the",
    "and",
    "estate",
    "vineyards",
    "vineyard",
    "winery",
    "cellars",
    "distillery",
    "tasting",
    "room",
    "cocktail",
    "lounge",
    "bar",
    "grill",
    "company",
    "co",
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

    conflict_groups = _mark_conflicting_occurrences(output)
    groups.extend(conflict_groups)
    return OccurrenceResolutionResult(events=output, groups=groups, skipped_low_quality=skipped)


def _mark_conflicting_occurrences(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Quarantine likely duplicate occurrences carrying materially different times."""
    parents = list(range(len(events)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parents[b] = a

    for left in range(len(events)):
        for right in range(left + 1, len(events)):
            if _is_conflicting_pair(events[left], events[right]):
                union(left, right)

    cohorts: dict[int, list[int]] = {}
    for index in range(len(events)):
        cohorts.setdefault(find(index), []).append(index)

    groups: list[dict[str, Any]] = []
    for indexes in cohorts.values():
        if len(indexes) < 2:
            continue
        details = tuple(
            detail
            for index in indexes
            for detail in _conflict_details(events[index])
        )
        reason = "same_date+same_canonical_venue+similar_title+conflicting_start_time"
        for index in indexes:
            events[index]["publication_blocker_reason"] = "conflicting_occurrence"
            events[index]["publication_blocker_details"] = list(details)
            add_decision(
                events[index],
                "occurrence_conflict",
                {"cohort_size": len(indexes)},
                1.0,
                reason,
            )
        groups.append(
            {
                "kind": "conflicting_occurrence",
                "canonical_title": events[indexes[0]].get("title"),
                "confidence": 1.0,
                "reason": reason,
                "source_events": list(details),
            }
        )
    return groups


def _is_conflicting_pair(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if _is_completed_captain_exclusion(left) or _is_completed_captain_exclusion(right):
        return False
    if normalize_text(left.get("start_date")) != normalize_text(right.get("start_date")):
        return False
    if not _venue_match_reason(left, right):
        return False
    delta = _time_delta_minutes(left.get("start_time"), right.get("start_time"))
    if delta is None or delta <= 10:
        return False
    if _explicit_distinct_session_formats(left, right):
        return False
    if _explicit_non_overlapping_age_cohorts(left, right):
        return False
    title_score, _ = _title_similarity(left, right)
    return title_score >= 0.92 or _strong_title_containment(left, right)


_AGE_COHORT_RE = re.compile(r"\bages?\s*(\d{1,2})\s*[-\N{EN DASH}\N{EM DASH}]\s*(\d{1,2})\b", re.IGNORECASE)


def _explicit_non_overlapping_age_cohorts(
    left: dict[str, Any], right: dict[str, Any]
) -> bool:
    """Keep explicitly disjoint age sessions from becoming a time conflict."""
    ranges: list[tuple[int, int]] = []
    for event in (left, right):
        match = _AGE_COHORT_RE.search(str(event.get("title") or ""))
        if not match:
            return False
        lower, upper = (int(value) for value in match.groups())
        if lower > upper:
            return False
        ranges.append((lower, upper))
    left_range, right_range = ranges
    return left_range[1] < right_range[0] or right_range[1] < left_range[0]


def _is_completed_captain_exclusion(event: dict[str, Any]) -> bool:
    return str(event.get("captain_disposition") or "").upper() == "EXCLUDE"


def _strong_title_containment(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Recognize a substantial shared title core without choosing a time authority."""
    a = set(_WORD_RE.findall(_identity_title(normalize_text(left.get("title")), left)))
    b = set(_WORD_RE.findall(_identity_title(normalize_text(right.get("title")), right)))
    if min(len(a), len(b)) < 3:
        return False
    overlap = len(a & b)
    return overlap >= 3 and overlap / min(len(a), len(b)) >= 0.75


def _explicit_distinct_session_formats(left: dict[str, Any], right: dict[str, Any]) -> bool:
    descriptions = [normalize_text(event.get("description")) for event in (left, right)]
    breakfast_evening = (
        bool(re.search(r"\b(?:breakfast|morning)\b", descriptions[0]))
        and bool(re.search(r"\bevening\b", descriptions[1]))
    ) or (
        bool(re.search(r"\b(?:breakfast|morning)\b", descriptions[1]))
        and bool(re.search(r"\bevening\b", descriptions[0]))
    )
    music_drag = (
        bool(re.search(r"\b(?:mini )?music festival\b|\bthree bands?\b", descriptions[0]))
        and bool(re.search(r"\bdrag show\b|\blip[ -]?sync", descriptions[1]))
    ) or (
        bool(re.search(r"\b(?:mini )?music festival\b|\bthree bands?\b", descriptions[1]))
        and bool(re.search(r"\bdrag show\b|\blip[ -]?sync", descriptions[0]))
    )
    return breakfast_evening or music_drag


def _conflict_details(event: dict[str, Any]) -> list[dict[str, Any]]:
    provenance = event.get("occurrence_provenance") or event.get("dedupe_provenance") or [event]
    identity = _venue_identity(event)
    details: list[dict[str, Any]] = []
    for item in provenance:
        title = str(item.get("title") or event.get("title") or "")
        details.append(
            {
                "source": item.get("source") or event.get("source"),
                "source_event_id": item.get("source_event_id") or event.get("source_event_id"),
                "source_url": item.get("url") or event.get("url"),
                "title": title,
                "normalized_title": _identity_title(normalize_text(title), event),
                "start_date": item.get("start_date") or event.get("start_date"),
                "start_time": item.get("start_time") or event.get("start_time"),
                "end_time": item.get("end_time") or event.get("end_time"),
                "venue": item.get("venue") or event.get("venue"),
                "venue_identity": identity,
                "reason": "conflicting_occurrence",
            }
        )
    return details


def _venue_identity(event: dict[str, Any]) -> str:
    ids = sorted(_venue_ids(event))
    if ids:
        return f"venue_id:{ids[0]}"
    names = sorted(_venue_names(event))
    return f"venue_name:{names[0]}" if names else "venue_unknown"


def compare_occurrences(left: dict[str, Any], right: dict[str, Any]) -> OccurrenceEvidence:
    """Return explainable evidence that two records describe one occurrence."""
    if normalize_text(left.get("start_date")) != normalize_text(right.get("start_date")):
        return OccurrenceEvidence(0.0, ("different_date",))

    left_disposition = str(left.get("production_disposition_cohort") or "").strip()
    right_disposition = str(right.get("production_disposition_cohort") or "").strip()
    if left_disposition and left_disposition == right_disposition:
        return OccurrenceEvidence(1.0, ("same_date", "same_production_disposition_cohort"))

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

    venue_match = _venue_match_reason(left, right)
    if venue_match:
        confidence += 0.32
        reasons.append(venue_match)
    else:
        return OccurrenceEvidence(confidence, tuple(reasons + ["different_venue"]))

    time_delta = _time_delta_minutes(left.get("start_time"), right.get("start_time"))
    nested_time_match = _nested_performance_window_matches(left, right) or _contained_celebration_window(left, right)
    if time_delta is not None and time_delta <= 10:
        confidence += 0.25
        reasons.append("start_time_within_10m")
    elif time_delta is None:
        # Missing time is not positive evidence. A merge can still succeed only with
        # exceptionally strong title and venue evidence.
        reasons.append("missing_start_time")
    elif nested_time_match:
        confidence += 0.25
        reasons.append("nested_performance_start_matches")
    else:
        return OccurrenceEvidence(confidence, tuple(reasons + ["different_start_time"]))

    title_score, title_reason = _title_similarity(left, right)
    if title_score >= 0.92:
        confidence += 0.28
        reasons.append(f"{title_reason}={title_score:.2f}")
    elif title_score >= 0.80:
        confidence += 0.22
        reasons.append(f"{title_reason}={title_score:.2f}")
    elif title_score >= 0.70 and (nested_time_match or (time_delta is not None and time_delta <= 10)):
        confidence += 0.18
        reasons.append(f"{title_reason}={title_score:.2f}")
    else:
        return OccurrenceEvidence(
            confidence,
            tuple(reasons + [f"{title_reason}={title_score:.2f}"]),
        )

    return OccurrenceEvidence(min(confidence, 1.0), tuple(reasons))


_NESTED_PERFORMANCE_TIME_RE = re.compile(
    r"\b(?:band|performance|music|takes? the [^.]{0,40})[^.]{0,100}?"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>a\.?m\.?|p\.?m\.?)?\s*"
    r"(?:[-\N{EN DASH}\N{EM DASH}]|to)",
    re.IGNORECASE,
)


def _nested_performance_window_matches(left: dict[str, Any], right: dict[str, Any]) -> bool:
    for evidence_event, timed_event in ((left, right), (right, left)):
        match = _NESTED_PERFORMANCE_TIME_RE.search(str(evidence_event.get("description") or ""))
        if not match:
            continue
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or 0)
        meridiem = (match.group("meridiem") or "").casefold().replace(".", "")
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        candidate_hours = {hour}
        if not meridiem and hour < 12:
            candidate_hours.add(hour + 12)
        if str(timed_event.get("start_time") or "") in {f"{candidate:02d}:{minute:02d}" for candidate in candidate_hours}:
            return True
    return False


def _contained_celebration_window(left: dict[str, Any], right: dict[str, Any]) -> bool:
    titles = " | ".join(normalize_text(event.get("title")) for event in (left, right))
    if not re.search(r"\b(?:anniversary|celebrat(?:ion|ing))\b", titles):
        return False
    title_score, _ = _title_similarity(left, right)
    if title_score < 0.75:
        return False
    left_end, right_end = str(left.get("end_time") or ""), str(right.get("end_time") or "")
    if not left_end or left_end != right_end:
        return False
    delta = _time_delta_minutes(left.get("start_time"), right.get("start_time"))
    return delta is not None and delta <= 120


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
        for url in sorted(_urls(event)):
            if url not in urls:
                urls.append(url)
        provenance.extend(
            event.get("occurrence_provenance")
            or event.get("dedupe_provenance")
            or [_summarize(event)]
        )

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
    left_ids = _venue_ids(left)
    right_ids = _venue_ids(right)
    if left_ids & right_ids:
        return "same_venue_id"

    left_names = _venue_names(left)
    right_names = _venue_names(right)
    if left_names & right_names:
        return "same_canonical_venue"
    return None


def _venue_ids(event: dict[str, Any]) -> set[str]:
    fields = ("venue_id", "parent_venue_id", "venue_parent_id")
    return {
        normalize_text(event.get(field))
        for field in fields
        if normalize_text(event.get(field))
    }


def _venue_names(event: dict[str, Any]) -> set[str]:
    fields = (
        "venue_registry_name",
        "venue",
        "parent_venue",
        "venue_parent",
        "organization",
    )
    names: set[str] = set()
    for field in fields:
        value = normalize_text(event.get(field))
        if not value:
            continue
        normalized = _normalize_venue_name(value)
        if normalized:
            names.add(normalized)
    return names


def _normalize_venue_name(value: str) -> str:
    words = [word for word in _WORD_RE.findall(value.casefold()) if word not in _VENUE_NOISE]
    return " ".join(words)


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
        "source_event_id": event.get("source_event_id"),
        "url": event.get("url"),
        "venue": event.get("venue"),
        "venue_id": event.get("venue_id"),
        "start_date": event.get("start_date"),
        "start_time": event.get("start_time"),
        "end_time": event.get("end_time"),
    }
