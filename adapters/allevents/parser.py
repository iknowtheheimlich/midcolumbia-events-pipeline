"""Normalize AllEvents city pages from embedded JSON-LD.

The collector deliberately ignores surrounding recommendation and FAQ prose. AllEvents
mixes local listings with nearby recommendations; geography remains a downstream concern.
"""

from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
import json
import re
from typing import Any, Iterable
from urllib.parse import urlparse

from adapters.contract import CanonicalEvent


_SPACE_RE = re.compile(r"\s+")
_EVENT_TYPES = {"event", "businessevent", "childrensevent", "comedyEvent".casefold(),
                "danceevent", "deliveryevent", "educationevent", "exhibitionevent",
                "festivalevent", "foodevent", "literaryevent", "musicevent",
                "publicationevent", "saleevent", "screeningevent", "socialevent",
                "sportsevent", "theaterevent", "visualartsevent"}


class _JsonLdExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capturing = False
        self._parts: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "script":
            return
        attributes = {key.casefold(): (value or "") for key, value in attrs}
        if attributes.get("type", "").casefold() == "application/ld+json":
            self._capturing = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "script" and self._capturing:
            self.blocks.append("".join(self._parts))
            self._capturing = False
            self._parts = []


def parse_pages(pages: dict[str, str] | Iterable[str]) -> list[CanonicalEvent]:
    """Parse one or more AllEvents city pages and deduplicate repeated listing URLs."""
    page_values = pages.values() if isinstance(pages, dict) else pages
    events: list[CanonicalEvent] = []
    seen: set[tuple[str, str, str]] = set()

    for html in page_values:
        for node in _event_nodes(html):
            event = _normalize_event(node)
            if event is None:
                continue
            identity = (
                str(event.get("url") or ""),
                str(event.get("start_date") or ""),
                str(event.get("start_time") or ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            events.append(event)

    return events


def _event_nodes(html: str) -> Iterable[dict[str, Any]]:
    extractor = _JsonLdExtractor()
    extractor.feed(html)
    for block in extractor.blocks:
        try:
            payload = json.loads(block)
        except (TypeError, json.JSONDecodeError):
            continue
        yield from _walk_events(payload)


def _walk_events(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _walk_events(item)
        return
    if not isinstance(value, dict):
        return

    node_type = value.get("@type")
    types = node_type if isinstance(node_type, list) else [node_type]
    if any(str(item).casefold() in _EVENT_TYPES for item in types if item):
        yield value

    graph = value.get("@graph")
    if graph is not None:
        yield from _walk_events(graph)
    items = value.get("itemListElement")
    if items is not None:
        yield from _walk_events(items)
    item = value.get("item")
    if item is not None:
        yield from _walk_events(item)


def _normalize_event(node: dict[str, Any]) -> CanonicalEvent | None:
    title = _text(node.get("name"))
    url = _text(node.get("url") or node.get("@id"))
    start = _parse_datetime(node.get("startDate"))
    if not title or not url or start is None:
        return None

    end = _parse_datetime(node.get("endDate"))
    location = node.get("location") if isinstance(node.get("location"), dict) else {}
    address = location.get("address") if isinstance(location.get("address"), dict) else {}
    organizer = node.get("organizer") if isinstance(node.get("organizer"), dict) else {}

    venue = _text(location.get("name")) or _text(address.get("streetAddress")) or "Online"
    city = _text(address.get("addressLocality"))
    state = _text(address.get("addressRegion"))
    street = _text(address.get("streetAddress"))
    postal = _text(address.get("postalCode"))
    full_address = _join_address(street, city, state, postal)

    event: CanonicalEvent = {
        "title": title,
        "description": _text(node.get("description")),
        "venue": venue,
        "city": city,
        "state": state,
        "address": full_address,
        "start_date": start.date().isoformat(),
        "start_time": start.strftime("%H:%M"),
        "end_date": end.date().isoformat() if end else None,
        "end_time": end.strftime("%H:%M") if end else None,
        "organization": _text(organizer.get("name")),
        "url": url,
        "external_url": url,
        "source": "AllEvents",
        "source_event_id": _source_id(url),
        "source_category": _source_category(node),
        "image_url": _image_url(node.get("image")),
        "event_status": _tail(node.get("eventStatus")),
        "attendance_mode": _tail(node.get("eventAttendanceMode")),
    }
    return {key: value for key, value in event.items() if value is not None}


def _parse_datetime(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def _source_category(node: dict[str, Any]) -> str | None:
    for field in ("eventType", "category", "keywords"):
        value = node.get(field)
        if isinstance(value, list):
            cleaned = [_text(item) for item in value]
            joined = ", ".join(item for item in cleaned if item)
            if joined:
                return joined
        text = _text(value)
        if text:
            return text
    return None


def _image_url(value: Any) -> str | None:
    if isinstance(value, list):
        return next((_image_url(item) for item in value if _image_url(item)), None)
    if isinstance(value, dict):
        return _text(value.get("url") or value.get("contentUrl"))
    return _text(value)


def _source_id(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    tail = path.rsplit("/", 1)[-1] if path else ""
    return tail or None


def _tail(value: Any) -> str | None:
    text = _text(value)
    return text.rsplit("/", 1)[-1] if text else None


def _join_address(*parts: str | None) -> str | None:
    values = [part for part in parts if part]
    return ", ".join(values) if values else None


def _text(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = _SPACE_RE.sub(" ", str(value)).strip()
    return text or None
