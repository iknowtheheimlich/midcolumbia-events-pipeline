"""Deterministic editorial policy for publisher-facing events.

Attempt_30_PublisherEditorialRules
Attempt_33_PublishingContract
Attempt_34_NotionPresentationLayer

This layer converts stable PublisherEvent projections into display-ready records.
Renderers should not contain venue aliases, URL selection, time formatting,
geographic policy, category policy, or publication-target routing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable

from src.publisher_projection import PublisherEvent
from src.publishing_contract import PublishingProfile, format_compact_range


_SPACE_RE = re.compile(r"\s+")

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
    """Display-ready event plus deterministic publication decisions."""

    title: str
    start_date: str
    end_date: str | None
    display_start_time: str | None
    display_end_time: str | None
    display_time: str | None
    display_venue: str
    display_city: str
    display_organization: str | None
    publication_url: str
    publication_disposition: str
    editorial_reason: str | None
    publication_target: str
    semantic_category: str | None
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


def apply_editorial_rules(
    event: PublisherEvent,
    profile: PublishingProfile | None = None,
) -> EditorialEvent:
    """Apply display cleanup and publication policy to one projected event."""
    active_profile = profile or PublishingProfile.load()
    display_city = _clean_optional(event.city) or ""
    display_venue = _display_venue(event, display_city)
    display_organization = _display_organization(event, display_venue)
    semantic_category = active_profile.normalize_category(event.category)
    explicit_target = getattr(event, "publication_target", None)
    publication_target = active_profile.publication_target(semantic_category, explicit_target)
    disposition, reason = _publication_disposition(event, publication_target)

    return EditorialEvent(
        title=_clean_text(event.title),
        start_date=event.start_date,
        end_date=event.end_date,
        display_start_time=event.start_time,
        display_end_time=event.end_time,
        display_time=format_compact_range(event.start_time, event.end_time),
        display_venue=display_venue,
        display_city=display_city,
        display_organization=display_organization,
        publication_url=_publication_url(event),
        publication_disposition=disposition,
        editorial_reason=reason,
        publication_target=publication_target,
        semantic_category=semantic_category,
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


def prepare_editorial_events(
    events: Iterable[PublisherEvent],
    profile: PublishingProfile | None = None,
) -> list[EditorialEvent]:
    """Apply editorial rules without changing event order."""
    active_profile = profile or PublishingProfile.load()
    return [apply_editorial_rules(event, active_profile) for event in events]


def auto_publish_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "AUTO_PUBLISH"]


def review_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "REVIEW"]


def rejected_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "REJECT"]


def main_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [
        event
        for event in events
        if event.publication_disposition == "AUTO_PUBLISH"
        and event.publication_target in {"MAIN", "BOTH"}
    ]


def community_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [
        event
        for event in events
        if event.publication_disposition == "AUTO_PUBLISH"
        and event.publication_target in {"COMMUNITY", "BOTH"}
    ]


def _publication_disposition(
    event: PublisherEvent,
    publication_target: str,
) -> tuple[str, str | None]:
    classification = (event.content_classification or "EVENT").upper()
    if event.content_rejection_reason or classification != "EVENT":
        return "REJECT", event.content_rejection_reason or f"content_{classification.casefold()}"
    if publication_target == "SUPPRESS":
        return "REJECT", "publication_suppressed"
    if publication_target == "REVIEW":
        return "REVIEW", "missing_or_unknown_category"
    if not event.city or not event.city.strip():
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
    for value in (event.external_url, event.eventbrite_url, event.source_url):
        if value and value.strip():
            return value.strip()
    return event.source_url


def _display_venue(event: PublisherEvent, city: str) -> str:
    if event.venue_reddit_combo:
        return _clean_text(event.venue_reddit_combo)

    venue = _normalize_venue(event.venue)
    parent = _normalize_venue(event.parent_venue) if event.parent_venue else None
    detail = _clean_optional(event.venue_detail)

    if city:
        venue = _remove_duplicate_city(venue, city)
        if parent:
            parent = _remove_duplicate_city(parent, city)
    if parent:
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
