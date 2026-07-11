"""Extract Eventbrite-linked events from already trusted local sources.

Attempt_24_Eventbrite_Bridge

Direct Eventbrite search harvesting is blocked by human verification. This
bridge preserves useful Eventbrite coverage already surfaced by active local
sources without adding a brittle scraper or changing the canonical schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlparse


EVENTBRITE_HOSTS = {"eventbrite.com", "www.eventbrite.com"}
EVENT_ID_RE = re.compile(r"-(?P<event_id>\d{8,})(?:[/?#]|$)")


@dataclass(frozen=True)
class EventbriteBridgeItem:
    event_id: str | None
    eventbrite_url: str
    title: str | None
    start_date: str | None
    start_time: str | None
    venue: str | None
    city: str | None
    source: str | None
    source_url: str | None


def is_eventbrite_url(value: Any) -> bool:
    """Return whether value is an Eventbrite HTTP(S) URL."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in EVENTBRITE_HOSTS


def extract_event_id(url: str) -> str | None:
    """Extract Eventbrite numeric event ID from a canonical event URL."""
    match = EVENT_ID_RE.search(url)
    return match.group("event_id") if match else None


def bridge_items(events: Iterable[dict[str, Any]]) -> list[EventbriteBridgeItem]:
    """Return deduplicated Eventbrite-linked events in stable order."""
    items: dict[str, EventbriteBridgeItem] = {}

    for event in events:
        eventbrite_url = first_eventbrite_url(event)
        if eventbrite_url is None:
            continue

        event_id = extract_event_id(eventbrite_url)
        key = event_id or eventbrite_url
        candidate = EventbriteBridgeItem(
            event_id=event_id,
            eventbrite_url=eventbrite_url,
            title=string_or_none(event.get("title")),
            start_date=string_or_none(event.get("start_date")),
            start_time=string_or_none(event.get("start_time")),
            venue=string_or_none(event.get("venue")),
            city=string_or_none(event.get("city")),
            source=string_or_none(event.get("source")),
            source_url=string_or_none(event.get("url")),
        )
        items.setdefault(key, candidate)

    return sorted(
        items.values(),
        key=lambda item: (
            item.start_date or "9999-12-31",
            item.start_time or "99:99",
            (item.title or "").casefold(),
        ),
    )


def first_eventbrite_url(event: dict[str, Any]) -> str | None:
    """Return first Eventbrite URL from canonical URL fields."""
    for field in ("external_url", "url"):
        value = event.get(field)
        if is_eventbrite_url(value):
            return str(value).strip()
    return None


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
