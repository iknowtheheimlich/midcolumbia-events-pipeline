"""Parse Richland Library LibCal monthly HTML fragments."""

from __future__ import annotations

import html
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

from adapters.richland_library.config import DEFAULT_CITY, DEFAULT_VENUE, SOURCE_NAME

EVENT_BLOCK_RE = re.compile(r'<div class="s-lc-mc-evt".*?</div>\s*</div>', re.DOTALL)
ANCHOR_RE = re.compile(r'<a\s+href="(?P<url>[^"]+)"(?P<attrs>.*?)>(?P<title>.*?)</a>', re.DOTALL)
DATA_CONTENT_RE = re.compile(r'data-content="(?P<content>.*?)"\s*>', re.DOTALL)
LOCATION_RE = re.compile(r'<div class="s-lc-mc-evt-loc">(?P<location>.*?)</div>', re.DOTALL)
TIME_RE = re.compile(r'<div class="s-lc-mc-evt-time">(?P<time>.*?)</div>', re.DOTALL)
DETAIL_ROW_RE = re.compile(r"<dt>(?P<label>.*?)</dt>\s*<dd>(?P<value>.*?)</dd>", re.DOTALL)
EVENT_ID_RE = re.compile(r"/event/(?P<id>\d+)")


def parse_monthly_html(fragment: str) -> list[dict[str, Any]]:
    """Parse a LibCal monthly calendar HTML fragment into canonical events."""
    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for block in EVENT_BLOCK_RE.findall(fragment):
        event = parse_event_block(block)
        if not event:
            continue
        source_event_id = str(event.get("source_event_id") or "")
        occurrence_key = f"{source_event_id}|{event.get('start_date')}|{event.get('start_time')}"
        if occurrence_key in seen_ids:
            continue
        seen_ids.add(occurrence_key)
        events.append(event)

    return events


def parse_event_block(block: str) -> dict[str, Any] | None:
    """Parse one LibCal event block."""
    anchor = ANCHOR_RE.search(block)
    if not anchor:
        return None

    url = html.unescape(anchor.group("url")).strip()
    title = clean_text(anchor.group("title"))
    source_event_id = extract_event_id(url)
    location = clean_text(match_or_empty(LOCATION_RE, block, "location"))
    visible_time = clean_text(match_or_empty(TIME_RE, block, "time"))
    details = parse_popover_details(block)

    start_date, start_time = parse_detail_datetime(details.get("From") or "")
    end_date, end_time = parse_detail_datetime(details.get("To") or "")

    if not start_time and visible_time:
        start_time = parse_time(visible_time)

    category = details.get("Audience")
    description = details.get("Description")
    presenter = details.get("Presenter")

    return {
        "title": title,
        "venue": location or DEFAULT_VENUE,
        "venue_id": None,
        "address": None,
        "city": DEFAULT_CITY,
        "start_date": start_date,
        "end_date": end_date or start_date,
        "start_time": start_time,
        "end_time": end_time,
        "url": url,
        "source": SOURCE_NAME,
        "category": category,
        "description": description,
        "source_event_id": source_event_id,
        "source_room": location or None,
        "presenter": presenter,
    }


def parse_popover_details(block: str) -> dict[str, str]:
    """Parse LibCal popover details from the anchor data-content attribute."""
    match = DATA_CONTENT_RE.search(block)
    if not match:
        return {}

    content = html.unescape(match.group("content"))
    details: dict[str, str] = {}

    for row in DETAIL_ROW_RE.finditer(content):
        label = clean_text(row.group("label"))
        value = clean_text(row.group("value"))
        if label:
            details[label] = value

    return details


def parse_detail_datetime(value: str) -> tuple[str | None, str | None]:
    """Parse strings like '1:00 PM Wednesday, July 1st, 2026'."""
    text = remove_ordinals(value)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None, None

    for fmt in ("%I:%M %p %A, %B %d, %Y", "%I %p %A, %B %d, %Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date().isoformat(), parsed.strftime("%H:%M")
        except ValueError:
            continue

    return None, None


def parse_time(value: str) -> str | None:
    """Parse a visible time string."""
    text = value.strip()
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def remove_ordinals(value: str) -> str:
    """Remove English ordinal suffixes from dates."""
    return re.sub(r"(\d+)(st|nd|rd|th)", r"\1", value)


def extract_event_id(url: str) -> str | None:
    """Extract LibCal numeric event ID from a URL."""
    match = EVENT_ID_RE.search(url)
    return match.group("id") if match else None


def match_or_empty(pattern: re.Pattern[str], text: str, group: str) -> str:
    match = pattern.search(text)
    return match.group(group) if match else ""


def clean_text(value: str | None) -> str | None:
    """Strip HTML tags and normalize whitespace."""
    if value is None:
        return None
    text = html.unescape(value)
    text = _TextExtractor.extract(text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


class _TextExtractor(HTMLParser):
    """Tiny HTML-to-text extractor."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    @classmethod
    def extract(cls, value: str) -> str:
        parser = cls()
        parser.feed(value)
        return " ".join(parser.parts)
