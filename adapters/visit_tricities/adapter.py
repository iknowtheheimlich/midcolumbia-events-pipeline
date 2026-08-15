"""Visit Tri-Cities source adapter.

Milestone: Attempt_15_Visit_Tri-Cities

Visit Tri-Cities renders event listings client-side. The useful event payload
appears as Algolia-style hit objects, not ordinary static HTML.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlsplit

from adapters.algolia.payload import extract_hits
from adapters.visit_tricities.config import BASE_URL, SOURCE_NAME
from src.recurrence_classifier import classify_event_kind


def parse_visit_tricities_html(html: str) -> list[dict]:
    """Legacy placeholder for static HTML parsing.

    Visit Tri-Cities currently appears to be JavaScript/API-backed. Prefer
    `parse_visit_tricities_payload` with saved JSON fixtures.
    """
    if not isinstance(html, str):
        raise TypeError("html must be a string")

    return []


def parse_visit_tricities_payload(payload: dict[str, Any] | list[Any]) -> list[dict]:
    """Parse a saved Visit Tri-Cities/Algolia payload into canonical events.

    Supported payload shapes:
    - a raw list of hit dictionaries
    - {"hits": [...]}
    - {"results": [{"hits": [...]}]}
    """
    hits = extract_hits(payload)
    return [normalize_hit(hit) for hit in hits if isinstance(hit, dict)]


def normalize_hit(hit: dict[str, Any]) -> dict:
    """Normalize a Visit Tri-Cities Algolia hit into the canonical event schema."""
    start_dt = unix_to_utc_datetime(hit.get("startDate"))
    end_dt = unix_to_utc_datetime(hit.get("endDate"))

    url = normalize_url(hit.get("uri"))
    venue = first_non_empty(hit.get("eventLocation"), first_address_line(hit.get("address")))
    named_venue = corroborated_named_venue(hit)
    if named_venue and venue.casefold() == (city_from_address(hit.get("address")) or city_from_regions(hit.get("partnerRegions"))).casefold():
        venue = named_venue
    city = city_from_address(hit.get("address")) or city_from_regions(hit.get("partnerRegions"))

    event = {
        "title": clean_text(hit.get("title")),
        "venue": clean_text(venue),
        "venue_id": None,
        "address": address_to_string(hit.get("address")),
        "city": city or "",
        "start_date": date_part(start_dt),
        "end_date": date_part(end_dt),
        "start_time": time_part(start_dt, hit.get("isAllDay")),
        "end_time": time_part(end_dt, hit.get("isAllDay")),
        "url": url,
        "source": SOURCE_NAME,
        "category": first_category(hit.get("eventCategories")),
        "description": clean_text(hit.get("content")),
        # Optional VTC/series metadata. These fields must not be required by downstream consumers.
        "external_url": clean_text(hit.get("website")) or None,
        "source_is_multi_day": bool(hit.get("isMultiDay")),
        "recurrence_note": clean_text(hit.get("readableRepeatRule")) or None,
        "source_event_id": clean_text(hit.get("objectID") or hit.get("id")) or None,
        "source_start_timestamp": int_or_none(hit.get("startDate")),
        "source_end_timestamp": int_or_none(hit.get("endDate")),
    }
    event["event_kind"] = classify_event_kind(event)
    event["is_series"] = event["event_kind"] == "series"
    return event


def unix_to_utc_datetime(value: Any) -> datetime | None:
    """Convert a Unix timestamp to UTC datetime."""
    if value in (None, ""):
        return None

    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def normalize_url(value: Any) -> str:
    """Return an absolute Visit Tri-Cities event URL when possible."""
    text = clean_text(value)
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text.startswith("/"):
        return f"{BASE_URL}{text}"
    return f"{BASE_URL}/{text}"


def clean_text(value: Any) -> str:
    """Normalize simple text fields."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def first_non_empty(*values: Any) -> str:
    """Return the first non-empty normalized value."""
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def first_address_line(value: Any) -> str:
    """Return the first address line when address is a list."""
    if isinstance(value, list) and value:
        return clean_text(value[0])
    return ""


def address_to_string(value: Any) -> str | None:
    """Convert address list/string to a single string."""
    if isinstance(value, list):
        text = ", ".join(clean_text(item) for item in value if clean_text(item))
        return text or None
    text = clean_text(value)
    return text or None


def city_from_address(value: Any) -> str:
    """Infer city from the final address line when possible."""
    if not isinstance(value, list):
        return ""

    for line in reversed(value):
        text = clean_text(line)
        if ", Washington" in text:
            return text.split(", Washington", 1)[0].strip()
        if " Washington" in text:
            return text.split(" Washington", 1)[0].strip()
    return ""


def city_from_regions(value: Any) -> str:
    """Infer Tri-Cities city from partner region strings."""
    if not isinstance(value, list):
        return ""

    known = ("Richland", "Kennewick", "Pasco", "West Richland", "Benton City", "Prosser")
    for item in value:
        text = clean_text(item)
        for city in known:
            if text == city or text.startswith(f"{city} »"):
                return city
    return ""


def date_part(value: datetime | None) -> str | None:
    """Return ISO date from datetime."""
    return value.date().isoformat() if value else None


def time_part(value: datetime | None, is_all_day: Any) -> str | None:
    """Return HH:MM time unless the event is all-day."""
    if value is None or is_all_day is True:
        return None
    return value.strftime("%H:%M")


def first_category(value: Any) -> str | None:
    """Return first category from a category list."""
    if isinstance(value, list):
        for item in value:
            text = clean_text(item)
            if text:
                return text
    text = clean_text(value)
    return text or None


def int_or_none(value: Any) -> int | None:
    """Return int(value) or None."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_TITLE_VENUE_RE = re.compile(r"\s+at\s+(?P<venue>[^|]+?)\s*$", re.IGNORECASE)


def corroborated_named_venue(hit: dict[str, Any]) -> str:
    """Recover a title venue only when description and destination corroborate it."""
    title = clean_text(hit.get("title"))
    match = _TITLE_VENUE_RE.search(title)
    if not match:
        return ""
    venue = clean_text(match.group("venue"))
    description = clean_text(hit.get("content"))
    if not venue or not re.search(rf"\bat\s+{re.escape(venue)}\b", description, re.IGNORECASE):
        return ""
    hostname = urlsplit(clean_text(hit.get("website"))).hostname or ""
    venue_token = re.sub(r"\b(?:the|winery|cellars?|brewing|company|co)\b", "", venue, flags=re.IGNORECASE)
    venue_token = re.sub(r"[^a-z0-9]", "", venue_token.casefold())
    host_token = re.sub(r"[^a-z0-9]", "", hostname.casefold())
    return venue if len(venue_token) >= 4 and venue_token in host_token else ""
