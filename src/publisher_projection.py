"""Projection layer between enriched pipeline events and publishers.

Attempt_29_PublisherModelAdapter
Attempt_34_NotionPresentationLayer
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from adapters.eventbrite.bridge import extract_event_id, first_eventbrite_url


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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_urls"] = list(self.source_urls)
        payload["duplicate_sources"] = list(self.duplicate_sources)
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
