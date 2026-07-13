"""Group sibling editorial occurrences into publisher-facing programs.

Attempt_41_ProgramIntelligence
Attempt_42_ExplainableIntelligence

This layer does not deduplicate sources. It groups legitimate occurrences of the
same cleaned program after editorial styling while preserving every occurrence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable

from src.intelligence import IntelligenceDecision
from src.publisher_editorial import EditorialEvent

_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ProgramOccurrence:
    start_date: str
    display_start_time: str | None
    display_end_time: str | None
    display_time: str | None
    display_venue: str
    display_city: str
    publication_url: str
    source: str
    source_event_id: str | None


@dataclass(frozen=True)
class EditorialProgram:
    title: str
    start_date: str
    semantic_category: str | None
    publication_target: str
    publication_disposition: str
    occurrences: tuple[ProgramOccurrence, ...]
    canonical_titles: tuple[str, ...]
    grouping_reason: str
    grouping_confidence: float = 1.0
    intelligence: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def display_start_time(self) -> str | None:
        return self.occurrences[0].display_start_time if self.occurrences else None


def group_editorial_programs(events: Iterable[EditorialEvent]) -> list[EditorialProgram]:
    """Group same-day sibling occurrences using a conservative exact key."""
    grouped: dict[tuple[str, str, str, str, str], list[EditorialEvent]] = {}
    order: list[tuple[str, str, str, str, str]] = []

    for event in events:
        key = _program_key(event)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(event)

    programs: list[EditorialProgram] = []
    for key in order:
        rows = sorted(grouped[key], key=_occurrence_sort_key)
        programs.append(_build_program(rows))
    return programs


def _program_key(event: EditorialEvent) -> tuple[str, str, str, str, str]:
    return (
        _normalize(event.title),
        event.semantic_category or "",
        event.publication_target,
        event.start_date,
        event.source,
    )


def _build_program(events: list[EditorialEvent]) -> EditorialProgram:
    first = events[0]
    occurrences = tuple(
        ProgramOccurrence(
            start_date=event.start_date,
            display_start_time=event.display_start_time,
            display_end_time=event.display_end_time,
            display_time=event.display_time,
            display_venue=event.display_venue,
            display_city=event.display_city,
            publication_url=event.publication_url,
            source=event.source,
            source_event_id=event.source_event_id,
        )
        for event in events
    )
    canonical_titles = tuple(
        dict.fromkeys((event.canonical_title or event.title) for event in events)
    )
    distinct_venues = len({(_normalize(item.display_venue), _normalize(item.display_city)) for item in occurrences})
    distinct_times = len({(item.display_start_time, item.display_end_time) for item in occurrences})
    reason = "single_occurrence"
    if len(occurrences) > 1:
        signals = ["exact_display_title", "same_day", "same_category", "same_source"]
        if distinct_venues > 1:
            signals.append("multiple_venues")
        if distinct_times > 1:
            signals.append("multiple_times")
        reason = "+".join(signals)

    confidence = 1.0
    decision = IntelligenceDecision(
        value=first.title,
        confidence=confidence,
        reason=reason,
    )

    return EditorialProgram(
        title=first.title,
        start_date=first.start_date,
        semantic_category=first.semantic_category,
        publication_target=first.publication_target,
        publication_disposition=first.publication_disposition,
        occurrences=occurrences,
        canonical_titles=canonical_titles,
        grouping_reason=reason,
        grouping_confidence=confidence,
        intelligence={"program_grouping": decision.to_dict()},
    )


def _occurrence_sort_key(event: EditorialEvent) -> tuple[int, str, str]:
    value = event.display_start_time or "99:99"
    try:
        hour, minute = value.split(":", 1)
        minutes = int(hour) * 60 + int(minute[:2])
    except (ValueError, TypeError):
        minutes = 24 * 60 + 1
    return minutes, event.display_city.casefold(), event.display_venue.casefold()


def _normalize(value: str) -> str:
    return _SPACE_RE.sub(" ", value.casefold().strip())
