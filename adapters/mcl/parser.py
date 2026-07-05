"""Parse Mid-Columbia Libraries listing HTML into canonical events."""

from __future__ import annotations

import html
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from adapters.mcl.config import BASE_URL, SOURCE_NAME

DATE_RE = re.compile(r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})(?:\s+[A-Z][a-z]{2})?$")
TIME_RANGE_RE = re.compile(r"^(?P<start>.+?)\s*-\s*(?P<end>.+)$")

BRANCH_CITY_MAP = {
    "Basin City": "Basin City",
    "Benton City": "Benton City",
    "Connell": "Connell",
    "Kahlotus": "Kahlotus",
    "Keewaydin Park": "Kennewick",
    "Kennewick": "Kennewick",
    "Merrill's Corner": "Pasco",
    "Othello": "Othello",
    "Pasco": "Pasco",
    "Prosser": "Prosser",
    "West Pasco": "Pasco",
    "West Richland": "West Richland",
}

EVENT_TYPES = [
    "Adult Program",
    "Author Visit",
    "Book Club",
    "Branch Closure",
    "Community Program",
    "Elementary Program",
    "Friends Event",
    "Lecture",
    "Library Tour",
    "Preschool Program",
    "School Visit",
    "Special Event",
    "Storytime",
    "Teen Program",
]

AUDIENCES = ["Teens 13+", "All Ages", "Adults", "Teens", "6-12", "9-12", "6-8", "0-5"]


class Link:
    def __init__(self, text: str, href: str) -> None:
        self.text = text
        self.href = href


def parse_listing_html(fragment: str, *, year: int) -> list[dict[str, Any]]:
    return parse_tokens(_Extractor.extract(fragment), year=year)


def parse_tokens(tokens: list[str | Link], *, year: int) -> list[dict[str, Any]]:
    events = []
    current_date = None
    i = 0

    while i < len(tokens):
        token = tokens[i]
        text = token.text if isinstance(token, Link) else token
        parsed_date = parse_date(text, year)

        if parsed_date:
            current_date = parsed_date
            i += 1
            continue

        if current_date and isinstance(token, Link):
            event, i = parse_event(tokens, i, current_date)
            events.append(event)
            continue

        i += 1

    return events


def parse_event(tokens: list[str | Link], i: int, start_date: str) -> tuple[dict[str, Any], int]:
    link = tokens[i]
    assert isinstance(link, Link)

    time_text = str(tokens[i + 1]) if i + 1 < len(tokens) else ""
    start_time, end_time = parse_time_range(time_text)

    description = str(tokens[i + 2]) if i + 2 < len(tokens) else None
    meta = str(tokens[i + 3]) if i + 3 < len(tokens) else ""

    branch, category, audience = parse_meta(meta)
    venue = f"Mid-Columbia Library ({branch})" if branch else "Mid-Columbia Library"
    city = BRANCH_CITY_MAP.get(branch or "", "Unknown")

    return {
        "title": clean(link.text),
        "venue": venue,
        "venue_id": None,
        "address": None,
        "city": city,
        "start_date": start_date,
        "end_date": start_date,
        "start_time": start_time,
        "end_time": end_time,
        "url": urljoin(BASE_URL, link.href),
        "source": SOURCE_NAME,
        "category": category,
        "description": clean(description),
        "source_branch": branch,
        "source_audience": audience,
    }, i + 4


def parse_date(value: str, year: int) -> str | None:
    match = DATE_RE.match(clean(value) or "")
    if not match:
        return None
    return datetime.strptime(f"{match.group('month')} {match.group('day')} {year}", "%b %d %Y").date().isoformat()


def parse_time_range(value: str) -> tuple[str | None, str | None]:
    text = clean(value) or ""
    match = TIME_RANGE_RE.match(text)
    if not match:
        return parse_time(text), None

    start = match.group("start").strip()
    end = match.group("end").strip()

    if not re.search(r"[ap]m$", start, re.I):
        suffix = re.search(r"([ap]m)$", end, re.I)
        if suffix:
            start += suffix.group(1)

    return parse_time(start), parse_time(end)


def parse_time(value: str) -> str | None:
    text = (clean(value) or "").lower().replace(" ", "")
    for fmt in ("%I:%M%p", "%I%p", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return None


def parse_meta(value: str) -> tuple[str | None, str | None, str | None]:
    text = clean(value) or ""

    for branch in sorted(BRANCH_CITY_MAP, key=len, reverse=True):
        if text.startswith(branch):
            rest = text[len(branch):].strip()
            category = next((x for x in EVENT_TYPES if rest.startswith(x)), None)
            if category:
                rest = rest[len(category):].strip()
            audience = next((x for x in AUDIENCES if rest.startswith(x)), None)
            return branch, category, audience

    return None, None, None


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return text or None


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens = []
        self.href = None
        self.parts = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.flush_text()
            self.href = dict(attrs).get("href", "")
            self.parts = []
        elif tag in {"div", "p", "td", "tr", "li", "h2", "h3"}:
            self.flush_text()

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            text = clean(" ".join(self.parts))
            if text:
                self.tokens.append(Link(text, self.href))
            self.href = None
            self.parts = []
        elif tag in {"div", "p", "td", "tr", "li", "h2", "h3"}:
            self.flush_text()

    def handle_data(self, data):
        if self.href is not None:
            self.parts.append(data)
        else:
            self.text_parts.append(data)

    def flush_text(self):
        text = clean(" ".join(self.text_parts))
        if text:
            self.tokens.append(text)
        self.text_parts = []

    @classmethod
    def extract(cls, value):
        parser = cls()
        parser.feed(value)
        parser.flush_text()
        return parser.tokens
