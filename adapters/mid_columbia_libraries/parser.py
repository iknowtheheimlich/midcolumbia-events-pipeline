"""Parse Mid-Columbia Libraries event listing HTML."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from adapters.mid_columbia_libraries.config import (
    AUDIENCES,
    BASE_URL,
    BRANCH_CITY_MAP,
    DEFAULT_VENUE_PREFIX,
    EVENT_TYPES,
    SOURCE_NAME,
)

DATE_RE = re.compile(r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})(?:\s+[A-Z][a-z]{2})?$")
TIME_RANGE_RE = re.compile(r"^(?P<start>.+?)\s*-\s*(?P<end>.+)$")
EVENT_ID_RE = re.compile(r"/(?:events|event)/(?P<id>[^/?#]+)")


@dataclass(frozen=True)
class LinkToken:
    text: str
    href: str


def parse_listing_html(fragment: str, *, year: int | None = None) -> list[dict[str, Any]]:
    """Parse an MCL events listing page into canonical event dictionaries."""
    tokens = _ListingExtractor.extract(fragment)
    return parse_listing_tokens(tokens, year=year or datetime.now().year)


def parse_listing_tokens(tokens: list[str | LinkToken], *, year: int) -> list[dict[str, Any]]:
    """Parse extracted listing tokens into events."""
    events: list[dict[str, Any]] = []
    index = 0
    current_date: str | None = None
    seen: set[tuple[str, str | None, str | None, str]] = set()

    while index < len(tokens):
        token = tokens[index]
        text = token.text if isinstance(token, LinkToken) else str(token)
        parsed_date = parse_listing_date(text, year=year)
        if parsed_date:
            current_date = parsed_date
            index += 1
            continue

        if current_date and isinstance(token, LinkToken):
            event, next_index = parse_event_at(tokens, index, current_date)
            index = next_index
            if event:
                key = (
                    event["title"],
                    event.get("start_date"),
                    event.get("start_time"),
                    event.get("venue", ""),
                )
                if key not in seen:
                    seen.add(key)
                    events.append(event)
            continue

        index += 1

    return events


def parse_event_at(tokens: list[str | LinkToken], index: int, start_date: str) -> tuple[dict[str, Any] | None, int]:
    """Parse one event beginning at a title link token."""
    link = tokens[index]
    if not isinstance(link, LinkToken):
        return None, index + 1

    title = clean_text(link.text)
    if not title:
        return None, index + 1

    cursor = index + 1
    time_text = next_text(tokens, cursor)
    if time_text:
        cursor += 1
    start_time, end_time = parse_time_range(time_text or "")

    description_parts: list[str] = []
    branch: str | None = None
    event_type: str | None = None
    audience: str | None = None

    while cursor < len(tokens):
        token = tokens[cursor]
        text = token.text if isinstance(token, LinkToken) else str(token)
        text = clean_text(text)
        if not text:
            cursor += 1
            continue
        if parse_listing_date(text, year=datetime.fromisoformat(start_date).year) or isinstance(token, LinkToken):
            break

        branch, event_type, audience = parse_meta_line(text)
        if branch:
            cursor += 1
            break

        description_parts.append(text)
        cursor += 1

    description = clean_description(" ".join(description_parts))
    venue = normalize_venue(branch)
    city = normalize_city(branch)
    url = urljoin(BASE_URL, link.href)

    return (
        {
            "title": title,
            "venue": venue,
            "venue_id": None,
            "address": None,
            "city": city,
            "start_date": start_date,
            "end_date": start_date,
            "start_time": start_time,
            "end_time": end_time,
            "url": url,
            "source": SOURCE_NAME,
            "category": event_type,
            "description": description,
            "source_event_id": extract_event_id(url),
            "source_branch": branch,
            "source_audience": audience,
        },
        cursor,
    )


def parse_listing_date(value: str, *, year: int) -> str | None:
    """Parse listing dates like 'Jul 7 Tue'."""
    match = DATE_RE.match(clean_text(value) or "")
    if not match:
        return None
    date_text = f"{match.group('month')} {match.group('day')} {year}"
    try:
        return datetime.strptime(date_text, "%b %d %Y").date().isoformat()
    except ValueError:
        return None


def parse_time_range(value: str) -> tuple[str | None, str | None]:
    """Parse MCL time strings into HH:MM values."""
    text = clean_text(value) or ""
    match = TIME_RANGE_RE.match(text)
    if not match:
        return parse_time(text), None

    start_raw = match.group("start").strip()
    end_raw = match.group("end").strip()
    start_raw = inherit_meridiem(start_raw, end_raw)
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
    """Parse common MCL time formats into HH:MM."""
    text = (clean_text(value) or "").lower().replace(" ", "")
    if not text:
        return None
    for fmt in ("%I:%M%p", "%I%p", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def parse_meta_line(value: str) -> tuple[str | None, str | None, str | None]:
    """Parse the trailing location/type/audience line."""
    text = clean_text(value) or ""
    for branch in sorted(BRANCH_CITY_MAP, key=len, reverse=True):
        if not text.startswith(branch):
            continue
        rest = text[len(branch) :].strip()
        event_type = first_matching_prefix(rest, EVENT_TYPES)
        if event_type:
            rest = rest[len(event_type) :].strip()
        audience = first_matching_prefix(rest, AUDIENCES)
        return branch, event_type, audience
    return None, None, None


def first_matching_prefix(value: str, options: set[str]) -> str | None:
    """Return the longest option matching the start of value."""
    text = value.strip()
    for option in sorted(options, key=len, reverse=True):
        if text.startswith(option):
            return option
    return None


def normalize_venue(branch: str | None) -> str:
    """Return the raw venue string for downstream Venue Registry resolution."""
    if not branch:
        return DEFAULT_VENUE_PREFIX
    if branch in {"Offsite", "Online", "Multiple Branches", "Rural Services"}:
        return branch
    return f"{DEFAULT_VENUE_PREFIX} ({branch})"


def normalize_city(branch: str | None) -> str:
    """Normalize branch to city while avoiding address hardcoding."""
    if not branch:
        return "Unknown"
    return BRANCH_CITY_MAP.get(branch, branch)


def clean_description(value: str | None) -> str | None:
    """Normalize description text."""
    return clean_text(value)


def extract_event_id(url: str) -> str | None:
    """Extract a stable source event identifier when available."""
    match = EVENT_ID_RE.search(url)
    return match.group("id") if match else None


def next_text(tokens: list[str | LinkToken], index: int) -> str | None:
    """Return the next token text."""
    if index >= len(tokens):
        return None
    token = tokens[index]
    return token.text if isinstance(token, LinkToken) else str(token)


def clean_text(value: str | None) -> str | None:
    """Decode HTML entities and normalize whitespace."""
    if value is None:
        return None
    text = html.unescape(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


class _ListingExtractor(HTMLParser):
    """Extract ordered visible text tokens and title links from listing HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str | LinkToken] = []
        self._link_href: str | None = None
        self._link_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.flush_text()
            attrs_dict = dict(attrs)
            self._link_href = attrs_dict.get("href") or ""
            self._link_parts = []
        elif tag in {"br", "p", "div", "li", "td", "th", "tr", "h2", "h3"}:
            self.flush_text()

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link_href is not None:
            text = clean_text(" ".join(self._link_parts))
            if text:
                self.tokens.append(LinkToken(text=text, href=self._link_href))
            self._link_href = None
            self._link_parts = []
        elif tag in {"p", "div", "li", "td", "th", "tr", "h2", "h3"}:
            self.flush_text()

    def handle_data(self, data: str) -> None:
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
