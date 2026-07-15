"""Read-only drift detection for active venue and organizer category priors."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from src.organizer_category_intelligence import normalize_organizer_name
from src.venue_category_intelligence import normalize_venue_name


@dataclass(frozen=True)
class DriftResult:
    entity_type: str
    entity_name: str
    expected_category: str
    recent_events: int
    expected_count: int
    expected_percent: float
    dominant_category: str | None
    dominant_percent: float
    change_magnitude: float
    status: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_knowledge_drift(
    events: Iterable[dict[str, Any]],
    *,
    venue_hints: Mapping[str, Any] | None = None,
    organizer_hints: Mapping[str, Any] | None = None,
    recent_limit: int = 20,
    minimum_recent_events: int = 5,
    watch_threshold: float = 0.20,
    drift_threshold: float = 0.35,
) -> list[DriftResult]:
    """Compare active hint categories with recent classified event behavior."""
    event_list = list(events)
    results: list[DriftResult] = []
    if venue_hints:
        results.extend(
            _detect_for_type(
                event_list,
                entity_type="venue",
                hints=venue_hints,
                fields=("venue_registry_name", "venue", "display_venue"),
                normalizer=normalize_venue_name,
                recent_limit=recent_limit,
                minimum_recent_events=minimum_recent_events,
                watch_threshold=watch_threshold,
                drift_threshold=drift_threshold,
            )
        )
    if organizer_hints:
        results.extend(
            _detect_for_type(
                event_list,
                entity_type="organizer",
                hints=organizer_hints,
                fields=("organizer_registry_name", "organization", "organizer", "host", "presented_by"),
                normalizer=normalize_organizer_name,
                recent_limit=recent_limit,
                minimum_recent_events=minimum_recent_events,
                watch_threshold=watch_threshold,
                drift_threshold=drift_threshold,
            )
        )
    rank = {"DRIFT": 0, "WATCH": 1, "STABLE": 2, "INSUFFICIENT": 3}
    return sorted(results, key=lambda item: (rank[item.status], item.entity_type, item.entity_name.casefold()))


def _detect_for_type(events, *, entity_type, hints, fields, normalizer, recent_limit, minimum_recent_events, watch_threshold, drift_threshold):
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        name = _first_text(event, fields)
        category = _text(event.get("category"))
        if not name or not category:
            continue
        grouped[normalizer(name)].append(event)

    output: list[DriftResult] = []
    for key, raw_hint in hints.items():
        expected, display = _hint_values(key, raw_hint)
        normalized = normalizer(display or key)
        rows = sorted(grouped.get(normalized, []), key=_event_sort_key, reverse=True)[:recent_limit]
        counts = Counter(_text(row.get("category")) for row in rows)
        counts.pop(None, None)
        total = sum(counts.values())
        expected_count = counts.get(expected, 0)
        expected_percent = expected_count / total if total else 0.0
        dominant, dominant_count = counts.most_common(1)[0] if counts else (None, 0)
        dominant_percent = dominant_count / total if total else 0.0
        change = 1.0 - expected_percent if total else 0.0
        if total < minimum_recent_events:
            status, recommendation = "INSUFFICIENT", "keep"
        elif change >= drift_threshold:
            status, recommendation = "DRIFT", "review_hint"
        elif change >= watch_threshold:
            status, recommendation = "WATCH", "monitor"
        else:
            status, recommendation = "STABLE", "keep"
        output.append(DriftResult(
            entity_type=entity_type,
            entity_name=display or key,
            expected_category=expected,
            recent_events=total,
            expected_count=expected_count,
            expected_percent=round(expected_percent, 4),
            dominant_category=dominant,
            dominant_percent=round(dominant_percent, 4),
            change_magnitude=round(change, 4),
            status=status,
            recommendation=recommendation,
        ))
    return output


def _hint_values(key: str, raw: Any) -> tuple[str, str]:
    if hasattr(raw, "category"):
        return str(raw.category), str(getattr(raw, "organizer_name", None) or getattr(raw, "venue_name", None) or key)
    if isinstance(raw, dict):
        category = raw.get("category_hint") or raw.get("category")
        display = raw.get("canonical_name") or raw.get("organizer_name") or raw.get("venue_name") or key
        return str(category or ""), str(display)
    return str(raw), str(key)


def _first_text(event: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = _text(event.get(field))
        if value:
            return value
    return None


def _event_sort_key(event: dict[str, Any]) -> str:
    return _text(event.get("start_date") or event.get("date") or event.get("event_date")) or ""


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
