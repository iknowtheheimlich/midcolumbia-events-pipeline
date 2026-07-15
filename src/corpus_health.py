"""Health metrics for the durable classified-event corpus."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class CorpusHealth:
    total_events: int
    distinct_sources: int
    distinct_categories: int
    distinct_venues: int
    distinct_organizers: int
    missing_venue: int
    missing_date: int
    missing_source: int
    category_distribution: dict[str, int]
    source_distribution: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_corpus_health(events: Iterable[dict[str, Any]]) -> CorpusHealth:
    rows = list(events)
    categories = Counter(_text(row.get("category")) for row in rows)
    sources = Counter(_text(row.get("source")) for row in rows)
    categories.pop(None, None)
    sources.pop(None, None)

    venue_values = []
    organizer_values = []
    for row in rows:
        venue_values.append(_text(row.get("venue_registry_name") or row.get("canonical_venue") or row.get("venue")))
        organizer_values.append(_text(row.get("organizer_registry_name") or row.get("canonical_organizer") or row.get("organization") or row.get("organizer") or row.get("host") or row.get("presented_by")))

    return CorpusHealth(
        total_events=len(rows),
        distinct_sources=len(sources),
        distinct_categories=len(categories),
        distinct_venues=len({value for value in venue_values if value}),
        distinct_organizers=len({value for value in organizer_values if value}),
        missing_venue=sum(value is None for value in venue_values),
        missing_date=sum(not _text(row.get("start_date")) for row in rows),
        missing_source=sum(not _text(row.get("source")) for row in rows),
        category_distribution=dict(sorted(categories.items(), key=lambda item: (-item[1], item[0].casefold()))),
        source_distribution=dict(sorted(sources.items(), key=lambda item: (-item[1], item[0].casefold()))),
    )


def render_corpus_health(health: CorpusHealth) -> str:
    lines = [
        "Attempt 78 Corpus Health",
        "========================",
        "",
        f"Total events: {health.total_events}",
        f"Distinct sources: {health.distinct_sources}",
        f"Distinct categories: {health.distinct_categories}",
        f"Distinct venues: {health.distinct_venues}",
        f"Distinct organizers: {health.distinct_organizers}",
        f"Missing venue: {health.missing_venue}",
        f"Missing date: {health.missing_date}",
        f"Missing source: {health.missing_source}",
        "",
        "CATEGORY DISTRIBUTION",
        "---------------------",
    ]
    lines.extend(f"{name}: {count}" for name, count in health.category_distribution.items())
    if not health.category_distribution:
        lines.append("None")
    lines.extend(["", "SOURCE DISTRIBUTION", "-------------------"])
    lines.extend(f"{name}: {count}" for name, count in health.source_distribution.items())
    if not health.source_distribution:
        lines.append("None")
    return "\n".join(lines).rstrip() + "\n"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
