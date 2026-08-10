"""Projection layer between enriched pipeline events and publishers.

Attempt_29_PublisherModelAdapter
Attempt_34_NotionPresentationLayer
Attempt_38_CategoryIntelligence
Attempt_42_ExplainableIntelligence
Attempt_50_VenuePresentationProfile
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from adapters.eventbrite.bridge import extract_event_id, first_eventbrite_url
from src.intelligence import normalize_intelligence
from src.venue_presentation import present_event


@dataclass(frozen=True)
class PublisherEvent:
    """Stable publisher-facing projection of one enriched canonical event."""

    title: str
    start_date: str
    end_date: str | None
    start_time: str | None
    end_time: str | None
    venue: str
    parent_venue: str | None
    venue_detail: str | None
    venue_id: str | None
    venue_type: str | None
    organization: str | None
    city: str | None
    state: str | None
    geographic_scope: str | None
    region: str | None
    location_type: str | None
    content_classification: str | None
    content_rejection_reason: str | None
    source: str
    source_event_id: str | None
    source_url: str
    source_urls: tuple[str, ...]
    external_url: str | None
    eventbrite_url: str | None
    eventbrite_event_id: str | None
    category: str | None
    description: str | None
    duplicate_sources: tuple[str, ...]
    duplicate_count: int
    publication_target: str | None = None
    venue_reddit_combo: str | None = None
    venue_website: str | None = None
    venue_registry_name: str | None = None
    display_venue: str | None = None
    display_city: str | None = None
    display_url: str | None = None
    venue_presentation_reason: str | None = None
    suppress_display_city: bool = False
    category_confidence: float | None = None
    category_reason: str | None = None
    organization_url: str | None = None
    artist: str | None = None
    artist_url: str | None = None
    publication_blocker_reason: str | None = None
    publication_blocker_details: tuple[dict[str, Any], ...] = ()
    intelligence: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_urls"] = list(self.source_urls)
        payload["duplicate_sources"] = list(self.duplicate_sources)
        payload["publication_blocker_details"] = list(self.publication_blocker_details)
        return payload


def project_event(event: dict[str, Any]) -> PublisherEvent:
    eventbrite_url = first_eventbrite_url(event)
    duplicate_sources = _string_tuple(
        event.get("duplicate_sources") or event.get("sources") or event.get("source_names")
    )
    source_urls = _string_tuple(event.get("source_urls"))
    source_url = _required_text(event, "url")
    if not source_urls:
        source_urls = (source_url,)
    presentation = present_event(event)

    return PublisherEvent(
        title=_required_text(event, "title"),
        start_date=_required_text(event, "start_date"),
        end_date=_optional_text(event.get("end_date")),
        start_time=_optional_text(event.get("start_time")),
        end_time=_optional_text(event.get("end_time")),
        venue=_required_text(event, "venue"),
        parent_venue=_first_text(event, "parent_venue", "venue_parent"),
        venue_detail=_optional_text(event.get("venue_detail")),
        venue_id=_optional_text(event.get("venue_id")),
        venue_type=_first_text(event, "venue_type", "registry_venue_type"),
        organization=_first_text(event, "organization", "organizer", "host"),
        city=_optional_text(event.get("city")),
        state=_optional_text(event.get("state")),
        geographic_scope=_optional_text(event.get("geo_scope")),
        region=_optional_text(event.get("geo_region")),
        location_type=_optional_text(event.get("location_type")),
        content_classification=_first_text(
            event, "content_kind", "content_classification", "content_type", "classification"
        ),
        content_rejection_reason=_first_text(
            event, "content_rejection_reason", "rejection_reason"
        ),
        source=_required_text(event, "source"),
        source_event_id=_optional_text(event.get("source_event_id")),
        source_url=source_url,
        source_urls=source_urls,
        external_url=_optional_text(event.get("external_url")),
        eventbrite_url=eventbrite_url,
        eventbrite_event_id=extract_event_id(eventbrite_url) if eventbrite_url else None,
        category=_optional_text(event.get("category")),
        description=_optional_text(event.get("description")),
        duplicate_sources=duplicate_sources,
        duplicate_count=_positive_int(event.get("duplicate_count"), default=max(1, len(duplicate_sources))),
        publication_target=_first_text(event, "publication_target", "publisher_target"),
        venue_reddit_combo=_optional_text(event.get("venue_reddit_combo")),
        venue_website=_optional_text(event.get("venue_website")),
        venue_registry_name=_optional_text(event.get("venue_registry_name")),
        display_venue=presentation.display_name,
        display_city=None if presentation.suppress_city else presentation.display_city,
        display_url=presentation.display_url,
        venue_presentation_reason=presentation.reason,
        suppress_display_city=presentation.suppress_city,
        category_confidence=_optional_float(event.get("category_confidence")),
        category_reason=_optional_text(event.get("category_reason")),
        organization_url=_optional_text(event.get("organization_url")),
        artist=_first_text(event, "artist_registry_name", "artist", "performer"),
        artist_url=_optional_text(event.get("artist_url")),
        publication_blocker_reason=_optional_text(event.get("publication_blocker_reason")),
        publication_blocker_details=tuple(event.get("publication_blocker_details") or ()),
        intelligence=normalize_intelligence(event.get("intelligence")),
    )


def project_events(events: Iterable[dict[str, Any]]) -> list[PublisherEvent]:
    return [project_event(event) for event in events]


def _required_text(event: dict[str, Any], field: str) -> str:
    value = _optional_text(event.get(field))
    if value is None:
        raise ValueError(f"publisher projection requires non-empty {field!r}")
    return value


def _first_text(event: dict[str, Any], *fields: str) -> str | None:
    for field in fields:
        value = _optional_text(event.get(field))
        if value is not None:
            return value
    return None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        candidates = [value]
    else:
        try:
            candidates = list(value)
        except TypeError:
            candidates = [value]
    result: list[str] = []
    for candidate in candidates:
        text = _optional_text(candidate)
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
