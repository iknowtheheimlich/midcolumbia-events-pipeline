"""Visit Tri-Cities source adapter.

Milestone: Attempt_15_Visit_Tri-Cities

Visit Tri-Cities renders event listings client-side. The useful event payload
appears as Algolia-style hit objects, not ordinary static HTML.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SOURCE_NAME = "VisitTriCities"
VTC_BASE_URL = "https://www.visittri-cities.com"


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


def extract_hits(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    """Extract Algolia-style hits from common response shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict or list")

    if isinstance(payload.get("hits"), list):
        return [item for item in payload["hits"] if isinstance(item, dict)]

    results = payload.get("results")
    if isinstance(results, list):
        hits: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, dict) and isinstance(result.get("hits"), list):
                hits.extend(item for item in result["hits"] if isinstance(item, dict))
        return hits

    return []


def normalize_hit(hit: dict[str, Any]) -> dict:
    """Normalize a Visit Tri-Cities Algolia hit into the canonical event schema."""
    start_dt = unix_to_utc_datetime(hit.get("startDate"))
    end_dt = unix_to_utc_datetime(hit.get("endDate"))

    url = normalize_url(hit.get("uri"))
    venue = first_non_empty(hit.get("eventLocation"), first_address_line(hit.get("address")))
    city = city_from_address(hit.get("address")) or city_from_regions(hit.get("partnerRegions"))

    return {
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
    }


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
        return f"{VTC_BASE_URL}{text}"
    return f"{VTC_BASE_URL}/{text}"


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
