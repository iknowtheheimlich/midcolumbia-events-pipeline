"""Deterministic editorial policy for publisher-facing events.

Attempt_30_PublisherEditorialRules

This layer converts stable PublisherEvent projections into display-ready records.
Renderers should not contain venue aliases, URL selection, time formatting, or
geographic publication policy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable

from src.publisher_projection import PublisherEvent


_SPACE_RE = re.compile(r"\s+")
_TIME_RE = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::\d{2})?$")

VENUE_ALIASES = {
    "mid-columbia libraries": "Mid-Columbia Library",
    "mid columbia libraries": "Mid-Columbia Library",
    "mid columbia library": "Mid-Columbia Library",
    "richland public library": "Richland Library",
}

AUTO_SCOPES = {None, "LOCAL"}
REVIEW_SCOPES = {"REVIEW", "REGIONAL_REVIEW"}
REJECT_SCOPES = {"OUT_OF_AREA"}


@dataclass(frozen=True)
class EditorialEvent:
    """Display-ready event plus a deterministic publication disposition."""

    title: str
    start_date: str
    end_date: str | None
    display_start_time: str | None
    display_end_time: str | None
    display_venue: str
    display_city: str
    display_organization: str | None
    publication_url: str
    publication_disposition: str
    editorial_reason: str | None
    source: str
    source_event_id: str | None
    venue_id: str | None
    venue_type: str | None
    geographic_scope: str | None
    region: str | None
    location_type: str | None
    category: str | None
    description: str | None
    eventbrite_event_id: str | None
    duplicate_sources: tuple[str, ...]
    duplicate_count: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["duplicate_sources"] = list(self.duplicate_sources)
        return payload


def apply_editorial_rules(event: PublisherEvent) -> EditorialEvent:
    """Apply display cleanup and publication policy to one projected event."""
    display_city = _clean_optional(event.city) or ""
    display_venue = _display_venue(event, display_city)
    display_organization = _display_organization(event, display_venue)
    disposition, reason = _publication_disposition(event)

    return EditorialEvent(
        title=_clean_text(event.title),
        start_date=event.start_date,
        end_date=event.end_date,
        display_start_time=format_time(event.start_time),
        display_end_time=format_time(event.end_time),
        display_venue=display_venue,
        display_city=display_city,
        display_organization=display_organization,
        publication_url=_publication_url(event),
        publication_disposition=disposition,
        editorial_reason=reason,
        source=event.source,
        source_event_id=event.source_event_id,
        venue_id=event.venue_id,
        venue_type=event.venue_type,
        geographic_scope=event.geographic_scope,
        region=event.region,
        location_type=event.location_type,
        category=event.category,
        description=event.description,
        eventbrite_event_id=event.eventbrite_event_id,
        duplicate_sources=event.duplicate_sources,
        duplicate_count=event.duplicate_count,
    )


def prepare_editorial_events(events: Iterable[PublisherEvent]) -> list[EditorialEvent]:
    """Apply editorial rules without changing event order."""
    return [apply_editorial_rules(event) for event in events]


def auto_publish_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    """Return only events cleared for automatic rendering."""
    return [event for event in events if event.publication_disposition == "AUTO_PUBLISH"]


def review_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    """Return events requiring human geographic or data review."""
    return [event for event in events if event.publication_disposition == "REVIEW"]


def rejected_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    """Return events deterministically excluded from publication."""
    return [event for event in events if event.publication_disposition == "REJECT"]


def format_time(value: str | None) -> str | None:
    """Format canonical 24-hour time as compact Reddit display time."""
    if not value:
        return None
    text = value.strip()
    match = _TIME_RE.fullmatch(text)
    if not match:
        return text
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    if hour > 23 or minute > 59:
        return text
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def _publication_disposition(event: PublisherEvent) -> tuple[str, str | None]:
    classification = (event.content_classification or "EVENT").upper()
    if event.content_rejection_reason or classification != "EVENT":
        return "REJECT", event.content_rejection_reason or f"content_{classification.casefold()}"

    if not event.city:
        return "REVIEW", "missing_city"

    scope = event.geographic_scope
    if scope in REJECT_SCOPES:
        return "REJECT", "out_of_area"
    if scope in REVIEW_SCOPES:
        return "REVIEW", "geographic_review"
    if scope in AUTO_SCOPES:
        return "AUTO_PUBLISH", None
    return "REVIEW", "unknown_geographic_scope"


def _publication_url(event: PublisherEvent) -> str:
    """Prefer the most direct event or registration URL available."""
    for value in (event.external_url, event.eventbrite_url, event.source_url):
        if value and value.strip():
            return value.strip()
    return event.source_url


def _display_venue(event: PublisherEvent, city: str) -> str:
    venue = _normalize_venue(event.venue)
    parent = _normalize_venue(event.parent_venue) if event.parent_venue else None
    detail = _clean_optional(event.venue_detail)

    venue = _remove_duplicate_city(venue, city)
    if parent:
        parent = _remove_duplicate_city(parent, city)
        if detail and detail.casefold() not in {venue.casefold(), parent.casefold()}:
            return f"{detail}, {parent}"
        if venue.casefold() != parent.casefold():
            return f"{venue}, {parent}"
    return venue


def _display_organization(event: PublisherEvent, display_venue: str) -> str | None:
    organization = _clean_optional(event.organization)
    if not organization:
        return None
    normalized = _normalize_venue(organization)
    suppressed = {
        display_venue.casefold(),
        _normalize_venue(event.venue).casefold(),
    }
    if event.parent_venue:
        suppressed.add(_normalize_venue(event.parent_venue).casefold())
    return None if normalized.casefold() in suppressed else normalized


def _remove_duplicate_city(venue: str, city: str) -> str:
    if not city:
        return venue
    escaped = re.escape(city)
    cleaned = re.sub(rf"\s*(?:,|\s+-\s+)\s*{escaped}\s*$", "", venue, flags=re.IGNORECASE)
    return cleaned.strip()


def _normalize_venue(value: str) -> str:
    cleaned = _clean_text(value)
    return VENUE_ALIASES.get(cleaned.casefold(), cleaned)


def _clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value.strip())


def _clean_optional(value: str | None) -> str | None:
    return _clean_text(value) if value and value.strip() else None
