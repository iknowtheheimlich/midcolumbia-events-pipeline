"""Structured AllEvents inventory collector.

Attempt_59_AllEventsStructuredAPI
Attempt_67_AllEventsWallClockTime

The browser's date inventory is served by a session-gated JSON endpoint rather than
the static city HTML. Some records contain true Unix UTC epochs while others encode
local wall-clock values as if they were UTC. The normalizer repairs only narrow,
explainable daytime-event anomalies and preserves ordinary UTC conversion otherwise.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
import html
from http.cookiejar import CookieJar
import json
import re
from typing import Any, Callable
import urllib.request
from urllib.parse import urlsplit, urlunsplit

from adapters.contract import CanonicalEvent
from adapters.harvest import HarvestResult, generated_raw_path, save_raw_fixture
from adapters.registry import AdapterInfo

SEARCH_URL = "https://allevents.in/api/index.php/events/web/qs/search_with_filters"
BOOTSTRAP_URL = "https://allevents.in/kennewick?ref=cityselect"
_SPACE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_OFFSET_RE = re.compile(r"^(?P<sign>[+-])(?P<hours>\d{2}):(?P<minutes>\d{2})$")
_OVERNIGHT_CUE_RE = re.compile(
    r"\b(?:midnight|overnight|late[ -]?night|after[ -]?party|sunrise|24[ -]?hour)\b",
    re.IGNORECASE,
)
_DAYTIME_EVENT_CUE_RE = re.compile(
    r"\b(?:market|5k|10k|half marathon|marathon|santa|family|camp|fair|festival|"
    r"brunch|lunch|class|workshop|movie|bingo|tea party|volleyball|fundraiser)\b",
    re.IGNORECASE,
)
_EMBEDDED_DAYTIME_RE = re.compile(
    r"\b(?:[6-9]|1[01])(?:\s*(?::\d{2})?\s*(?:a\.?m\.?)?|\s*[-–]\s*(?:[7-9]|1[0-2]))\b",
    re.IGNORECASE,
)

CITY_QUERIES: tuple[dict[str, str], ...] = (
    {"city": "Kennewick", "latitude": "46.2086683", "longitude": "-119.1199480"},
    {"city": "Richland-WA", "latitude": "46.2804200", "longitude": "-119.2751996"},
    {"city": "Pasco", "latitude": "46.2395793", "longitude": "-119.1005657"},
    {"city": "West Richland", "latitude": "46.3043015", "longitude": "-119.3614092"},
    {"city": "Prosser", "latitude": "46.2067997", "longitude": "-119.7689249"},
)


def harvest_allevents_api(
    adapter: AdapterInfo,
    *,
    week_start: date,
    days: int,
    fetch_json: Callable[..., Any] | None = None,
) -> HarvestResult:
    """Fetch and normalize the browser-equivalent date inventory."""
    responses: dict[str, Any] = {}
    failures: list[str] = []
    fetch_json = fetch_json or _build_session_fetcher()

    for day_offset in range(days):
        target = week_start + timedelta(days=day_offset)
        for city in CITY_QUERIES:
            key = f"{target.isoformat()}|{city['city']}"
            try:
                response = fetch_json(
                    SEARCH_URL,
                    body=json.dumps(_request_payload(target, city)).encode("utf-8"),
                    headers=_api_headers(),
                )
                if not isinstance(response, dict) or int(response.get("error", 0)) != 0:
                    raise RuntimeError(f"unexpected API response: {response!r}")
                responses[key] = response
            except Exception as exc:
                failures.append(f"{key}: {type(exc).__name__}: {exc}")

    if not responses:
        raise RuntimeError("AllEvents API fetch failed: " + " | ".join(failures))

    normalized = normalize_api_responses(responses)
    output_path = generated_raw_path(adapter)
    save_raw_fixture(output_path, responses)
    return HarvestResult(
        source_name=adapter.source_name,
        raw_fixture_path=adapter.raw_fixture_path,
        raw_output_path=output_path,
        normalized_fixture_path=adapter.fixture_path,
        raw_count=sum(len(_search_results(value)) for value in responses.values()),
        normalized_events=normalized,
        error=" | ".join(failures) if failures else None,
    )


def _build_session_fetcher() -> Callable[..., Any]:
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    bootstrap_request = urllib.request.Request(BOOTSTRAP_URL, headers=_bootstrap_headers())
    with opener.open(bootstrap_request, timeout=30) as response:
        response.read()

    def fetch_json(url: str, *, body: bytes, headers: dict[str, str]) -> Any:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with opener.open(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            text = response.read().decode(charset, errors="replace")
        return _decode_api_json(text)

    return fetch_json


def _decode_api_json(text: str) -> Any:
    cleaned = text.lstrip("\ufeff \t\r\n")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        prefix = cleaned[:160].replace("\r", "\\r").replace("\n", "\\n")
        raise RuntimeError(f"AllEvents returned non-JSON response prefix: {prefix!r}") from exc


def normalize_api_responses(responses: dict[str, Any]) -> list[CanonicalEvent]:
    events: list[CanonicalEvent] = []
    seen: set[tuple[str, str, str]] = set()
    for response in responses.values():
        for row in _search_results(response):
            event = normalize_api_event(row)
            if event is None:
                continue
            identity = (
                str(event.get("source_event_id") or ""),
                str(event.get("start_date") or ""),
                str(event.get("start_time") or ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            events.append(event)
    return events


def normalize_api_event(row: dict[str, Any]) -> CanonicalEvent | None:
    title = _clean(row.get("eventname_raw") or row.get("eventname"))
    source_id = _clean(row.get("event_id"))
    url = _clean(row.get("event_url") or row.get("share_url"))
    start, time_reason = _api_datetime(row, "start_time", title or "")
    if not title or not source_id or not url or start is None:
        return None

    end, end_reason = _api_datetime(row, "end_time", title)
    venue_data = row.get("venue") if isinstance(row.get("venue"), dict) else {}
    venue = _clean(venue_data.get("venue") or row.get("location")) or "Online"
    ticket_url, cost = _ticket_details(row)

    event: CanonicalEvent = {
        "title": title,
        "description": _clean_description(row.get("description")),
        "venue": venue,
        "city": _clean(venue_data.get("city")),
        "state": _clean(venue_data.get("state")),
        "address": _clean(venue_data.get("street") or venue_data.get("full_address") or row.get("location")),
        "latitude": _clean(venue_data.get("latitude")),
        "longitude": _clean(venue_data.get("longitude")),
        "start_date": start.date().isoformat(),
        "start_time": start.strftime("%H:%M"),
        "end_date": end.date().isoformat() if end else None,
        "end_time": end.strftime("%H:%M") if end else None,
        "url": _clean_url(url),
        "external_url": ticket_url or _clean_url(url),
        "ticket_url": ticket_url,
        "cost": cost,
        "source": "AllEvents",
        "source_event_id": source_id,
        "image_url": _clean(row.get("banner_url") or row.get("thumb_url_large") or row.get("thumb_url")),
        "source_category": _clean(row.get("label")),
        "recurring_event_details": row.get("recurring_event_details"),
        "source_time_reason": time_reason if time_reason == end_reason else f"start={time_reason};end={end_reason}",
    }
    return {key: value for key, value in event.items() if value not in (None, "", [], {})}


def _api_datetime(row: dict[str, Any], field: str, title: str) -> tuple[datetime | None, str]:
    value = row.get(field)
    try:
        stamp = int(str(value))
    except (TypeError, ValueError):
        return None, "missing_or_invalid_epoch"

    offset = _timezone_offset(row.get("timezone"), stamp)
    utc_instant = datetime.fromtimestamp(stamp, timezone.utc)
    local_instant = utc_instant.astimezone(offset)
    evidence = " ".join(
        str(value or "")
        for value in (title, row.get("description"), row.get("location"))
    )

    if _is_wall_clock_epoch(utc_instant, local_instant, offset, evidence):
        wall_clock = utc_instant.replace(tzinfo=offset)
        return wall_clock, "wall_clock_epoch_repaired"
    return local_instant, "utc_epoch_converted"


def _is_wall_clock_epoch(
    utc_instant: datetime,
    local_instant: datetime,
    offset: tzinfo,
    evidence: str,
) -> bool:
    """Detect the narrow AllEvents defect where local clock time is stored as UTC.

    We repair only negative-offset records that convert into 12–4:59 AM while the raw
    UTC clock is a plausible daytime hour, and only when the event text identifies a
    normally daytime program or embeds a daytime range. Explicit overnight cues win.
    """
    offset_delta = offset.utcoffset(utc_instant)
    if offset_delta is None or offset_delta >= timedelta(0):
        return False
    if not (0 <= local_instant.hour < 5 and 6 <= utc_instant.hour <= 12):
        return False
    if _OVERNIGHT_CUE_RE.search(evidence):
        return False
    return bool(_DAYTIME_EVENT_CUE_RE.search(evidence) or _EMBEDDED_DAYTIME_RE.search(evidence))


def _request_payload(target: date, city: dict[str, str]) -> dict[str, Any]:
    return {
        "query": None,
        "multi_category": None,
        "formats": None,
        "price": None,
        "start_date": f"{target.isoformat()} 00:00",
        "end_date": f"{target.isoformat()} 23:59",
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "city": city["city"],
        "country": "United States",
        "region_code": "WA",
        "search_scope": "city",
    }


def _api_headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://allevents.in",
        "Referer": BOOTSTRAP_URL,
        "X-Requested-With": "XMLHttpRequest",
        "yt": "application/json; charset=UTF-8",
        "User-Agent": _user_agent(),
    }


def _bootstrap_headers() -> dict[str, str]:
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": _user_agent(),
    }


def _user_agent() -> str:
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"


def _search_results(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        return []
    rows = response.get("search_result")
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _epoch_datetime(value: Any, offset_value: Any) -> datetime | None:
    """Compatibility helper retained for callers and tests expecting strict UTC epochs."""
    try:
        stamp = int(str(value))
    except (TypeError, ValueError):
        return None
    offset = _timezone_offset(offset_value, stamp)
    return datetime.fromtimestamp(stamp, timezone.utc).astimezone(offset)


def _timezone_offset(value: Any, stamp: int) -> tzinfo:
    match = _OFFSET_RE.match(str(value or ""))
    if match:
        direction = 1 if match.group("sign") == "+" else -1
        delta = timedelta(hours=int(match.group("hours")), minutes=int(match.group("minutes")))
        return timezone(direction * delta)
    return _pacific_offset(stamp)


def _pacific_offset(stamp: int) -> timezone:
    instant = datetime.fromtimestamp(stamp, timezone.utc)
    year = instant.year
    march_first = date(year, 3, 1)
    first_sunday_march = 1 + ((6 - march_first.weekday()) % 7)
    second_sunday_march = first_sunday_march + 7
    november_first = date(year, 11, 1)
    first_sunday_november = 1 + ((6 - november_first.weekday()) % 7)
    dst_start_utc = datetime(year, 3, second_sunday_march, 10, tzinfo=timezone.utc)
    dst_end_utc = datetime(year, 11, first_sunday_november, 9, tzinfo=timezone.utc)
    return timezone(timedelta(hours=-7 if dst_start_utc <= instant < dst_end_utc else -8))


def _ticket_details(row: dict[str, Any]) -> tuple[str | None, str | None]:
    ticket_url: str | None = None
    cost: str | None = None
    for candidate in (row.get("tickets"), row.get("ticket")):
        if not isinstance(candidate, dict):
            continue
        ticket_url = ticket_url or _clean(candidate.get("ticket_url") or candidate.get("url") or candidate.get("link"))
        cost = cost or _clean(candidate.get("price_display") or candidate.get("price") or candidate.get("ticket_price"))
        if candidate.get("is_free") is True:
            cost = "Free"
    return _clean_url(ticket_url) if ticket_url else None, cost


def _clean_description(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return _SPACE_RE.sub(" ", _TAG_RE.sub(" ", html.unescape(text))).strip() or None


def _clean_url(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    parts = urlsplit(text)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _clean(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = _SPACE_RE.sub(" ", html.unescape(str(value))).strip()
    return text or None
