"""Parse Tri-City Vibe WordPress-rendered event listing HTML."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from adapters.tricity_vibe.config import BASE_URL, DEFAULT_CATEGORY, SOURCE_NAME

DATE_LINE_RE = re.compile(
    r"^(?P<date>\d{1,2}/\d{1,2}/\d{4})(?:\s+(?P<weekday>[A-Za-z]+))?(?:\s+(?P<time>.+))?$"
)
TIME_RANGE_RE = re.compile(r"^(?P<start>.+?)\s*-\s*(?P<end>.+)$")
EVENT_PATH_RE = re.compile(r"/event/(?P<slug>[^/?#]+)/?")
CITY_STATE_RE = re.compile(r"^(?P<city>.+?),\s*(?P<state>[A-Z]{2})$")

WEEKDAY_TYPO_FIXES = {
    "thursady": "thursday",
}

TIME_TYPO_FIXES = {
    "6pjm": "6pm",
}


@dataclass(frozen=True)
class LinkToken:
    text: str
    href: str


@dataclass(frozen=True)
class DateLine:
    start_date: str
    time_text: str | None


def parse_events_html(fragment: str) -> list[dict[str, Any]]:
    """Parse the Tri-City Vibe events page into canonical event dictionaries."""
    tokens = _ListingExtractor.extract(fragment)
    return parse_listing_tokens(tokens)


def parse_listing_tokens(tokens: list[str | LinkToken]) -> list[dict[str, Any]]:
    """Parse extracted visible tokens into canonical event dictionaries."""
    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, str | None, str]] = set()
    index = 0

    while index < len(tokens):
        token = tokens[index]
        text = token.text if isinstance(token, LinkToken) else str(token)
        text = clean_text(text) or ""

        if text.lower() == "past events":
            break

        date_line = parse_date_line(text)
        if not date_line:
            index += 1
            continue

        event, next_index = parse_event_after_date(tokens, index + 1, date_line)
        index = next_index
        if not event:
            continue

        key = (
            event["title"],
            event.get("start_date"),
            event.get("start_time"),
            event.get("venue", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        events.append(event)

    return events


def parse_event_after_date(
    tokens: list[str | LinkToken], index: int, date_line: DateLine
) -> tuple[dict[str, Any] | None, int]:
    """Parse one event following a date/time line."""
    link_index = find_next_event_link(tokens, index)
    if link_index is None:
        return None, index + 1

    link = tokens[link_index]
    if not isinstance(link, LinkToken):
        return None, link_index + 1

    title = clean_text(link.text)
    url = urljoin(BASE_URL, link.href)
    venue = clean_text(next_plain_text(tokens, link_index + 1))
    city_state = clean_text(next_plain_text(tokens, link_index + 2))
    city = parse_city(city_state)
    start_time, end_time = parse_time_range(date_line.time_text or "")

    if not title or not venue or not city:
        return None, link_index + 1

    return (
        {
            "title": title,
            "venue": venue,
            "venue_id": None,
            "address": None,
            "city": city,
            "start_date": date_line.start_date,
            "end_date": date_line.start_date,
            "start_time": start_time,
            "end_time": end_time,
            "url": url,
            "source": SOURCE_NAME,
            "category": DEFAULT_CATEGORY,
            "description": None,
            "source_event_id": extract_event_id(url),
            "source_location": city_state,
        },
        link_index + 3,
    )


def find_next_event_link(tokens: list[str | LinkToken], index: int) -> int | None:
    """Return the next event link index before another date line appears."""
    cursor = index
    while cursor < len(tokens):
        token = tokens[cursor]
        text = token.text if isinstance(token, LinkToken) else str(token)
        if parse_date_line(text):
            return None
        if isinstance(token, LinkToken) and is_event_url(token.href):
            return cursor
        cursor += 1
    return None


def next_plain_text(tokens: list[str | LinkToken], index: int) -> str | None:
    """Return the next plain text token, skipping empty/link tokens."""
    cursor = index
    while cursor < len(tokens):
        token = tokens[cursor]
        if isinstance(token, LinkToken):
            cursor += 1
            continue
        text = clean_text(str(token))
        if text:
            return text
        cursor += 1
    return None


def parse_date_line(value: str) -> DateLine | None:
    """Parse listing date/time lines like '07/10/2026 Friday 6 - 9pm'."""
    text = clean_text(value) or ""
    match = DATE_LINE_RE.match(text)
    if not match:
        return None

    try:
        parsed_date = datetime.strptime(match.group("date"), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None

    weekday = normalize_weekday(match.group("weekday") or "")
    time_text = clean_time_text(match.group("time") or "")

    # Weekday is intentionally non-blocking. The live site has typos, and the
    # calendar date is the safer canonical value.
    _ = weekday

    return DateLine(start_date=parsed_date, time_text=time_text)


def normalize_weekday(value: str) -> str | None:
    """Normalize weekday text while tolerating known source typos."""
    text = (clean_text(value) or "").lower()
    if not text:
        return None
    return WEEKDAY_TYPO_FIXES.get(text, text)


def clean_time_text(value: str) -> str | None:
    """Normalize source time typos and whitespace."""
    text = (clean_text(value) or "").lower()
    if not text:
        return None
    text = TIME_TYPO_FIXES.get(text, text)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_time_range(value: str) -> tuple[str | None, str | None]:
    """Parse Tri-City Vibe time strings into HH:MM values."""
    text = clean_time_text(value) or ""
    if not text:
        return None, None

    match = TIME_RANGE_RE.match(text)
    if not match:
        return parse_time(text), None

    start_raw = inherit_meridiem(match.group("start").strip(), match.group("end").strip())
    end_raw = match.group("end").strip()
    return parse_time(start_raw), parse_time(end_raw)


def inherit_meridiem(start_raw: str, end_raw: str) -> str:
    """Add am/pm to the start time when only the end time specifies it."""
    if re.search(r"[ap]m$", start_raw, re.IGNORECASE):
        return start_raw
    suffix_match = re.search(r"([ap]m)$", end_raw, re.IGNORECASE)
    if suffix_match:
        return f"{start_raw}{suffix_match.group(1)}"
    return start_raw


def parse_time(value: str) -> str | None:
    """Parse common Tri-City Vibe time formats into HH:MM."""
    text = (clean_time_text(value) or "").replace(" ", "")
    if not text:
        return None
    for fmt in ("%I:%M%p", "%I%p", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def parse_city(value: str | None) -> str | None:
    """Return city from 'City, ST' strings."""
    text = clean_text(value)
    if not text:
        return None
    match = CITY_STATE_RE.match(text)
    if not match:
        return text
    return match.group("city")


def is_event_url(value: str) -> bool:
    """Return whether href points at a Tri-City Vibe event post."""
    path = urlparse(value).path
    return bool(EVENT_PATH_RE.search(path))


def extract_event_id(url: str) -> str | None:
    """Extract the stable event slug from a Tri-City Vibe event URL."""
    match = EVENT_PATH_RE.search(urlparse(url).path)
    return match.group("slug") if match else None


def clean_text(value: str | None) -> str | None:
    """Decode HTML entities and normalize whitespace."""
    if value is None:
        return None
    text = html.unescape(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


class _ListingExtractor(HTMLParser):
    """Extract ordered visible text tokens and event links from listing HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str | LinkToken] = []
        self._link_href: str | None = None
        self._link_parts: list[str] = []
        self._text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.flush_text()
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            self.flush_text()
            attrs_dict = dict(attrs)
            self._link_href = attrs_dict.get("href") or ""
            self._link_parts = []
        elif tag in {"br", "p", "div", "li", "td", "th", "tr", "h1", "h2", "h3", "h4", "h5", "article"}:
            self.flush_text()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "a" and self._link_href is not None:
            text = clean_text(" ".join(self._link_parts))
            if text:
                self.tokens.append(LinkToken(text=text, href=self._link_href))
            self._link_href = None
            self._link_parts = []
        elif tag in {"p", "div", "li", "td", "th", "tr", "h1", "h2", "h3", "h4", "h5", "article"}:
            self.flush_text()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._link_href is not None:
            self._link_parts.append(data)
        else:
            self._text_parts.append(data)

    def flush_text(self) -> None:
        text = clean_text(" ".join(self._text_parts))
        if text:
            self.tokens.append(text)
        self._text_parts = []

    @classmethod
    def extract(cls, value: str) -> list[str | LinkToken]:
        parser = cls()
        parser.feed(value)
        parser.flush_text()
        return parser.tokens
