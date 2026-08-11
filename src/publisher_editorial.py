"""Deterministic editorial policy for publisher-facing events."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Iterable

from src.editorial_style import derive_display_fields
from src.geography import classify_region, normalize_city
from src.intelligence import attach_intelligence, normalize_intelligence
from src.publisher_projection import PublisherEvent
from src.publishing_contract import PublishingProfile, format_compact_range
from src.url_canonicalizer import is_facebook_share_url, strip_tracking_parameters, validate_public_http_url

_SPACE_RE = re.compile(r"\s+")
_VENUE_MARKDOWN_RE = re.compile(
    r"^\[([^\]]+)\]\((https?://[^)]+)\)(?:\s*,\s*.*)?$", re.IGNORECASE
)
_POSTAL_CODE_RE = re.compile(r"(?:^|\s)\d{5}(?:-\d{4})?$")
_COUNTRY_NAMES = {"united states", "united states of america", "usa", "us"}
_US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
}
VENUE_ALIASES = {
    "mid-columbia libraries": "Mid-Columbia Library",
    "mid columbia libraries": "Mid-Columbia Library",
    "mid columbia library": "Mid-Columbia Library",
    "richland public library": "Richland Library",
}
AUTO_SCOPES = {None, "LOCAL"}
REVIEW_SCOPES = {"REVIEW", "REGIONAL_REVIEW"}
REJECT_SCOPES = {"OUT_OF_AREA"}
COMPLETED_REJECTION_REASONS = {"out_of_area", "publication_suppressed", "captain_excluded_this_week"}


@dataclass(frozen=True)
class EditorialEvent:
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
    category_confidence: float | None = None
    category_reason: str | None = None
    canonical_title: str | None = None
    style_reason: str | None = None
    display_organization_url: str | None = None
    display_artist: str | None = None
    display_artist_url: str | None = None
    publication_url_reason: str | None = None
    publication_blocker_details: tuple[dict[str, Any], ...] = ()
    intelligence: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["duplicate_sources"] = list(self.duplicate_sources)
        payload["publication_blocker_details"] = list(self.publication_blocker_details)
        return payload


def apply_editorial_rules(event: PublisherEvent, profile: PublishingProfile | None = None) -> EditorialEvent:
    active_profile = profile or PublishingProfile.load()
    display_city = _clean_optional(event.display_city or event.city) or ""
    base_venue = _display_venue(event, display_city)
    locality = _locality_only_venue(base_venue)
    locality_conflict = bool(
        locality
        and display_city
        and normalize_city(locality) != normalize_city(display_city)
    )
    presentation_city = "" if locality else display_city
    style_city = None if event.venue_reddit_combo or locality else display_city
    display_title, display_venue, style_reason = derive_display_fields(
        event.title, base_venue, style_city, category=event.category
    )
    if not _has_unbalanced_quotes(event.title) and _has_unbalanced_quotes(display_title):
        display_title = event.title
        style_reason = "+".join(filter(None, (style_reason, "balanced_quote_preserved")))
    display_organization = _display_organization(event, display_venue)
    semantic_category = active_profile.normalize_category(event.category)
    publication_target = active_profile.publication_target(
        semantic_category, getattr(event, "publication_target", None)
    )
    publication_url, publication_url_reason, url_blocker = _publication_url(event)
    disposition, reason = _publication_disposition(
        event,
        publication_target,
        display_venue=display_venue,
        display_title=display_title,
        url_blocker=url_blocker,
        presentation_review_reason=(
            "conflicting_locality_presentation" if locality_conflict else None
        ),
    )
    explanation = attach_intelligence(
        {"intelligence": normalize_intelligence(event.intelligence)},
        "display_style",
        {"title": display_title, "venue": display_venue},
        1.0,
        style_reason,
    )["intelligence"]
    explanation = attach_intelligence(
        {"intelligence": explanation},
        "venue_presentation",
        {
            "venue": display_venue,
            "city": presentation_city,
            "source_city": display_city,
            "url": event.display_url,
        },
        1.0,
        event.venue_presentation_reason or "legacy_fallback",
    )["intelligence"]
    return EditorialEvent(
        title=display_title,
        start_date=event.start_date,
        end_date=event.end_date,
        display_start_time=event.start_time,
        display_end_time=event.end_time,
        display_time=format_compact_range(event.start_time, event.end_time),
        display_venue=display_venue,
        display_city=presentation_city,
        display_organization=display_organization,
        publication_url=publication_url,
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
        category_confidence=event.category_confidence,
        category_reason=event.category_reason,
        canonical_title=event.title,
        style_reason=style_reason,
        display_organization_url=event.organization_url if display_organization else None,
        display_artist=_clean_optional(event.artist),
        display_artist_url=event.artist_url,
        publication_url_reason=publication_url_reason,
        publication_blocker_details=event.publication_blocker_details,
        intelligence=explanation,
    )


def prepare_editorial_events(events: Iterable[PublisherEvent], profile: PublishingProfile | None = None) -> list[EditorialEvent]:
    active_profile = profile or PublishingProfile.load()
    return [apply_editorial_rules(event, active_profile) for event in events]


def auto_publish_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "AUTO_PUBLISH"]


def review_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "REVIEW"]


def rejected_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "REJECT"]


def main_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "AUTO_PUBLISH" and event.publication_target in {"MAIN", "BOTH"}]


def community_events(events: Iterable[EditorialEvent]) -> list[EditorialEvent]:
    return [event for event in events if event.publication_disposition == "AUTO_PUBLISH" and event.publication_target in {"COMMUNITY", "BOTH"}]


def _publication_disposition(
    event: PublisherEvent,
    publication_target: str,
    *,
    display_venue: str,
    display_title: str,
    url_blocker: str | None,
    presentation_review_reason: str | None,
) -> tuple[str, str | None]:
    classification = (event.content_classification or "EVENT").upper()
    if event.content_rejection_reason or classification != "EVENT":
        return "REJECT", event.content_rejection_reason or f"content_{classification.casefold()}"
    if (event.captain_disposition or "").upper() == "EXCLUDE":
        return "REJECT", event.captain_disposition_reason or "captain_excluded_this_week"
    if event.publication_blocker_reason:
        return "REVIEW", event.publication_blocker_reason
    if presentation_review_reason:
        return "REVIEW", presentation_review_reason
    if _has_unbalanced_quotes(display_title):
        return "REVIEW", "malformed_title_punctuation"
    if not display_venue.strip():
        return "REVIEW", "missing_venue"
    if url_blocker:
        return "REVIEW", url_blocker
    if publication_target == "SUPPRESS":
        return "REJECT", "publication_suppressed"
    if publication_target == "REVIEW":
        return "REVIEW", "missing_or_unknown_category"
    if not event.city or not event.city.strip():
        return "REVIEW", "missing_city"
    if event.geographic_scope in REJECT_SCOPES:
        return "REJECT", "out_of_area"
    if event.geographic_scope in REVIEW_SCOPES:
        return "REVIEW", "geographic_review"
    if event.geographic_scope in AUTO_SCOPES:
        return "AUTO_PUBLISH", None
    return "REVIEW", "unknown_geographic_scope"


def _publication_url(event: PublisherEvent) -> tuple[str, str | None, str | None]:
    combo_url = _venue_combo_parts(event.venue_reddit_combo)[1]
    candidates = (
        ("venue_reddit_combo", combo_url),
        ("display_url", event.display_url),
        ("external_url", event.external_url),
        ("eventbrite_url", event.eventbrite_url),
        ("source_url", event.source_url),
    )
    for field, value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        text = strip_tracking_parameters(text)
        try:
            validate_public_http_url(text, field=field)
        except ValueError:
            if field == "external_url" and is_facebook_share_url(text):
                source = str(event.source_url or "").strip()
                try:
                    validate_public_http_url(source, field="source_url")
                except ValueError:
                    return text, None, "invalid_publication_url"
                return source, "external_facebook_share_rejected_source_fallback", None
            return text, None, "invalid_publication_url"
        return text, field, None
    return event.source_url, None, "invalid_publication_url"


def _display_venue(event: PublisherEvent, city: str) -> str:
    if event.venue_reddit_combo:
        combo_label, _ = _venue_combo_parts(event.venue_reddit_combo)
        venue = combo_label or _clean_text(event.venue_reddit_combo)
    elif event.display_venue:
        venue = _clean_text(event.display_venue)
    else:
        venue = _normalize_venue(event.venue)
        parent = _normalize_venue(event.parent_venue) if event.parent_venue else None
        detail = _clean_optional(event.venue_detail)
        if city:
            venue = _remove_duplicate_city(venue, city)
            if parent:
                parent = _remove_duplicate_city(parent, city)
        if parent:
            if detail and detail.casefold() not in {venue.casefold(), parent.casefold()}:
                venue = f"{detail}, {parent}"
            elif venue.casefold() != parent.casefold():
                venue = f"{venue}, {parent}"
    return _compact_publication_venue(venue, city)


def _venue_combo_parts(value: str | None) -> tuple[str | None, str | None]:
    text = _clean_optional(value)
    if not text:
        return None, None
    match = _VENUE_MARKDOWN_RE.fullmatch(text)
    if not match:
        return None, None
    return _clean_text(match.group(1)), match.group(2).strip()


def _compact_publication_venue(value: str, city: str) -> str:
    """Remove only a terminal city/geography suffix from a visible venue label."""
    cleaned = _clean_text(value)
    if not city:
        return cleaned
    parts = [part.strip() for part in cleaned.split(",")]
    city_key = city.strip().casefold()
    for index in range(len(parts) - 1, 0, -1):
        if parts[index].casefold() != city_key:
            continue
        suffix = parts[index + 1 :]
        if not suffix or all(_is_geographic_suffix(part) for part in suffix):
            compact = ", ".join(parts[:index]).strip()
            return compact or cleaned
    return cleaned


def _is_geographic_suffix(value: str) -> bool:
    text = _SPACE_RE.sub(" ", value.strip())
    without_postal = _POSTAL_CODE_RE.sub("", text).strip()
    if not without_postal:
        return True
    key = without_postal.casefold().rstrip(".")
    return (
        key in _COUNTRY_NAMES
        or key in _US_STATE_NAMES
        or bool(re.fullmatch(r"[A-Za-z]{2}", without_postal))
    )


def _locality_only_venue(value: str) -> str | None:
    """Return a known locality when the entire label is locality plus geography."""
    parts = [part.strip() for part in _clean_text(value).split(",")]
    if len(parts) < 2 or not all(_is_geographic_suffix(part) for part in parts[1:]):
        return None
    locality = normalize_city(parts[0])
    if not locality or classify_region(locality) == "UNKNOWN":
        return None
    return locality


def _display_organization(event: PublisherEvent, display_venue: str) -> str | None:
    organization = _clean_optional(event.organization)
    if not organization:
        return None
    normalized = _normalize_venue(organization)
    suppressed = {display_venue.casefold(), _normalize_venue(event.venue).casefold()}
    if event.parent_venue:
        suppressed.add(_normalize_venue(event.parent_venue).casefold())
    return None if normalized.casefold() in suppressed else normalized


def _remove_duplicate_city(venue: str, city: str) -> str:
    return re.sub(rf"\s*(?:,|\s+-\s+)\s*{re.escape(city)}\s*$", "", venue, flags=re.IGNORECASE).strip()


def _normalize_venue(value: str) -> str:
    cleaned = _clean_text(value)
    return VENUE_ALIASES.get(cleaned.casefold(), cleaned)


def _clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value.strip())


def _clean_optional(value: str | None) -> str | None:
    return _clean_text(value) if value and value.strip() else None


def _has_unbalanced_quotes(value: str) -> bool:
    """Detect visible unbalanced double quotes without treating apostrophes as quotes."""
    return value.count('"') % 2 == 1 or value.count("“") != value.count("”")
