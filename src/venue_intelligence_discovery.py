"""Discover venue-level category priors from classified event history.

Attempt_74_VenueIntelligenceDiscovery

This module only recommends candidates. It never mutates the active venue hint
registry. Promotion remains an explicit human decision.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from math import log2
import re
from typing import Any, Iterable

from src.venue_registry import normalize_venue_key

DEFAULT_EXCLUDED_VENUE_TYPES = {
    "bar",
    "brewery",
    "community center",
    "convention center",
    "fairgrounds",
    "hotel",
    "park",
    "restaurant",
    "winery",
}

_VENUE_NAME_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("winery", re.compile(r"\b(?:winery|vineyard|cellars?)\b", re.IGNORECASE)),
    ("brewery", re.compile(r"\b(?:brewery|brewing|brewpub)\b", re.IGNORECASE)),
    ("bar", re.compile(r"\b(?:bar|pub|saloon|tavern|lounge|spirits|distillery)\b", re.IGNORECASE)),
    ("restaurant", re.compile(r"\b(?:restaurant|kitchen|grill|cafe|bistro|eatery)\b", re.IGNORECASE)),
    ("hotel", re.compile(r"\b(?:hotel|inn|lodge|resort)\b", re.IGNORECASE)),
    ("fairgrounds", re.compile(r"\bfairgrounds?\b", re.IGNORECASE)),
    ("convention center", re.compile(r"\b(?:convention|conference) center\b", re.IGNORECASE)),
    ("community center", re.compile(r"\bcommunity center\b", re.IGNORECASE)),
    ("park", re.compile(r"\b(?:park|fairground|marina)\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class VenueIntelligenceCandidate:
    venue_name: str
    total_events: int
    dominant_category: str | None
    dominant_count: int
    dominant_percent: float
    second_category: str | None
    second_count: int
    second_percent: float
    distinct_categories: int
    entropy: float
    confidence: float
    recommendation: str
    reason: str
    venue_type: str | None = None
    last_seen: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def discover_venue_intelligence(
    events: Iterable[dict[str, Any]],
    *,
    minimum_events: int = 25,
    minimum_dominant_percent: float = 0.90,
    maximum_second_percent: float = 0.10,
    maximum_entropy: float = 0.55,
    excluded_venue_types: set[str] | None = None,
) -> list[VenueIntelligenceCandidate]:
    """Aggregate historical classifications and recommend venue priors."""
    excluded = {value.casefold() for value in (excluded_venue_types or DEFAULT_EXCLUDED_VENUE_TYPES)}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    display_names: dict[str, str] = {}

    for event in events:
        venue_name = _text(event.get("venue_registry_name") or event.get("venue") or event.get("display_venue"))
        category = _text(event.get("category"))
        if not venue_name or not category:
            continue
        key = normalize_venue_key(venue_name)
        if not key:
            continue
        display_names.setdefault(key, venue_name)
        grouped[key].append(event)

    candidates: list[VenueIntelligenceCandidate] = []
    for key, venue_events in grouped.items():
        category_counts = Counter(_text(event.get("category")) for event in venue_events)
        category_counts.pop(None, None)
        total = sum(category_counts.values())
        ranked = category_counts.most_common()
        dominant_category, dominant_count = ranked[0] if ranked else (None, 0)
        second_category, second_count = ranked[1] if len(ranked) > 1 else (None, 0)
        dominant_percent = dominant_count / total if total else 0.0
        second_percent = second_count / total if total else 0.0
        entropy = _normalized_entropy(category_counts)
        venue_name = display_names[key]
        venue_type = _dominant_text(venue_events, "registry_venue_type", "venue_type") or infer_venue_type(venue_name)
        last_seen = max((_event_date(event) for event in venue_events if _event_date(event)), default=None)

        recommendation, reason = _recommendation(
            total=total,
            dominant_percent=dominant_percent,
            second_percent=second_percent,
            entropy=entropy,
            venue_type=venue_type,
            minimum_events=minimum_events,
            minimum_dominant_percent=minimum_dominant_percent,
            maximum_second_percent=maximum_second_percent,
            maximum_entropy=maximum_entropy,
            excluded=excluded,
        )
        confidence = _confidence(total, dominant_percent, entropy)
        candidates.append(
            VenueIntelligenceCandidate(
                venue_name=venue_name,
                total_events=total,
                dominant_category=dominant_category,
                dominant_count=dominant_count,
                dominant_percent=round(dominant_percent, 4),
                second_category=second_category,
                second_count=second_count,
                second_percent=round(second_percent, 4),
                distinct_categories=len(category_counts),
                entropy=round(entropy, 4),
                confidence=round(confidence, 4),
                recommendation=recommendation,
                reason=reason,
                venue_type=venue_type,
                last_seen=last_seen,
            )
        )

    rank = {"PROMOTE": 0, "REVIEW": 1, "INSUFFICIENT": 2, "REJECT": 3}
    return sorted(candidates, key=lambda item: (rank[item.recommendation], -item.confidence, item.venue_name.casefold()))


def infer_venue_type(venue_name: str | None) -> str | None:
    """Infer obvious multipurpose venue types when registry metadata is absent."""
    text = _text(venue_name)
    if not text:
        return None
    for venue_type, pattern in _VENUE_NAME_TYPE_PATTERNS:
        if pattern.search(text):
            return venue_type
    return None


def _recommendation(
    *,
    total: int,
    dominant_percent: float,
    second_percent: float,
    entropy: float,
    venue_type: str | None,
    minimum_events: int,
    minimum_dominant_percent: float,
    maximum_second_percent: float,
    maximum_entropy: float,
    excluded: set[str],
) -> tuple[str, str]:
    if venue_type and venue_type.casefold() in excluded:
        return "REJECT", f"excluded_venue_type={venue_type}"
    if total < minimum_events:
        return "INSUFFICIENT", f"insufficient_sample={total}<{minimum_events}"
    if dominant_percent < minimum_dominant_percent:
        return "REJECT", f"dominant_percent={dominant_percent:.3f}<{minimum_dominant_percent:.3f}"
    if second_percent > maximum_second_percent:
        return "REJECT", f"second_percent={second_percent:.3f}>{maximum_second_percent:.3f}"
    if entropy > maximum_entropy:
        return "REJECT", f"entropy={entropy:.3f}>{maximum_entropy:.3f}"
    return "PROMOTE", "dominant_category_stable"


def _confidence(total: int, purity: float, entropy: float) -> float:
    """Conservative evidence confidence; sample size dominates early observations."""
    sample_factor = total / (total + 20.0) if total > 0 else 0.0
    stability_factor = max(0.0, 1.0 - entropy)
    return purity * sample_factor * stability_factor


def _normalized_entropy(counts: Counter[str | None]) -> float:
    total = sum(counts.values())
    categories = len(counts)
    if total <= 0 or categories <= 1:
        return 0.0
    raw = -sum((count / total) * log2(count / total) for count in counts.values() if count)
    return raw / log2(categories)


def _dominant_text(events: list[dict[str, Any]], *fields: str) -> str | None:
    values = Counter()
    for event in events:
        for field in fields:
            value = _text(event.get(field))
            if value:
                values[value] += 1
                break
    return values.most_common(1)[0][0] if values else None


def _event_date(event: dict[str, Any]) -> str | None:
    return _text(event.get("start_date") or event.get("date") or event.get("event_date"))


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
