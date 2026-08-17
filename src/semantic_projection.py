"""Shared semantic occurrence transformation for live and frozen cohorts."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable

from src.deduplicate import DeduplicationResult, deduplicate_events
from src.production_dispositions import ProductionDispositions
from src.source_attribution import quarantine_attribution_conflicts
from src.time_semantics import enrich_event_time_semantics

_MIDNIGHT = {"00:00", "00:00:00", "12:00 AM", "12:00AM"}


@dataclass(frozen=True)
class SemanticProjectionResult:
    events: list[dict[str, Any]] = field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)
    phantom_occurrences: list[dict[str, Any]] = field(default_factory=list)
    quarantined_sources: list[dict[str, Any]] = field(default_factory=list)
    skipped_low_quality: int = 0


def transform_semantic_occurrences(
    events: Iterable[dict[str, Any]], *,
    deduplicate: bool = True,
    apply_time_semantics: bool = False,
    production_dispositions: ProductionDispositions | None = None,
) -> SemanticProjectionResult:
    """Apply shared time, rollover, attribution, presentation, and dedupe policy."""
    working = [dict(event) for event in events]
    if production_dispositions is not None:
        working = production_dispositions.apply(working)
    if apply_time_semantics:
        working = [enrich_event_time_semantics(event) for event in working]

    retained: list[dict[str, Any]] = []
    phantoms: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for event in working:
        if _is_exclusive_end_occurrence(event):
            phantoms.append(event)
            continue
        event = _canonical_presentation(event)
        event = quarantine_attribution_conflicts(event)
        if event.get("publication_blocker_reason") == "source_attribution_conflict":
            quarantined.append(event)
        retained.append(event)

    result = deduplicate_events(retained) if deduplicate else DeduplicationResult(events=retained)
    _validate_captain_compatibility(result.duplicate_groups, retained)
    return SemanticProjectionResult(
        events=result.events,
        duplicate_groups=result.duplicate_groups,
        phantom_occurrences=phantoms,
        quarantined_sources=quarantined,
        skipped_low_quality=result.skipped_low_quality,
    )


def _is_exclusive_end_occurrence(event: dict[str, Any]) -> bool:
    occurrence = str(event.get("occurrence_date") or event.get("start_date") or "")
    source_start = str(event.get("source_start_date") or occurrence)
    source_end = str(event.get("source_end_date") or occurrence)
    evidence = event.get("source_time_evidence") or {}
    end_time = str(evidence.get("end_time") if isinstance(evidence, dict) else event.get("end_time") or "")
    return occurrence == source_end and source_start != source_end and end_time in _MIDNIGHT


def _canonical_presentation(event: dict[str, Any]) -> dict[str, Any]:
    copied = dict(event)
    venue = str(copied.get("venue") or "").strip()
    canonical = str(copied.get("canonical_venue") or copied.get("venue_registry_name") or "").strip()
    if canonical and re.search(r"(?:\s-|\b(?:of|at|in|the))\s*$", venue, re.IGNORECASE):
        copied["venue"] = canonical
        if copied.get("display_venue") == venue:
            copied["display_venue"] = canonical
    city = str(copied.get("city") or "").strip()
    copied["city"] = re.sub(r",?\s+WA\s*$", "", city, flags=re.IGNORECASE).strip()
    if copied.get("display_city") == city:
        copied["display_city"] = copied["city"]
    return copied


def _validate_captain_compatibility(groups: list[dict[str, Any]], events: list[dict[str, Any]]) -> None:
    by_identity: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for event in events:
        key = _identity(event)
        by_identity.setdefault(key, []).append(event)
    for group in groups:
        members=[]
        for summary in group.get("source_events", ()):
            matches=by_identity.get(_identity(summary), [])
            if matches: members.append(matches.pop(0))
        visible=[item for item in members if item.get("publication_blocker_reason")!="source_attribution_conflict"]
        if visible: members=visible
        for field in ("Captain Include", "Captain Category", "Captain Target", "Captain Title Override", "Captain Time Override", "Captains Venue Override", "Captain Description Override"):
            values={str(item.get("captain_state",{}).get(field) or "").strip() for item in members}
            values.discard("")
            if len(values)>1:
                raise ValueError(f"contradictory Captain decisions for semantic duplicate cohort: field={field} values={sorted(values)}")


def _identity(event: dict[str, Any]) -> tuple[str, str, str, str]:
    return tuple(str(event.get(field) or "").strip().casefold() for field in ("source", "source_event_id", "start_date", "title"))
