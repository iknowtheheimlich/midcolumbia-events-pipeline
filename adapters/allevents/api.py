"""Structured AllEvents inventory collector.

Attempt_59_AllEventsStructuredAPI
Attempt_67_AllEventsWallClockTime
Attempt_68_ExplicitDescriptionTimeEvidence

The browser's date inventory is served by a session-gated JSON endpoint rather than
the static city HTML. Some records contain true Unix UTC epochs while others encode
local wall-clock values as if they were UTC. Explicit source-authored AM/PM ranges in
the event description outrank conflicting epoch values; otherwise the normalizer uses
narrow wall-clock anomaly repair and ordinary UTC conversion.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
import html
from http.cookiejar import CookieJar
import json
import logging
import re
import time
from typing import Any, Callable
from urllib.error import URLError
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
_EXPLICIT_RANGE_RE = re.compile(
    r"(?<!\d)(?P<start_hour>\d{1,2})(?::(?P<start_minute>\d{2}))?\s*"
    r"(?P<start_meridiem>a\.?m\.?|p\.?m\.?)\s*(?:[-–—]|to)\s*"
    r"(?P<end_hour>\d{1,2})(?::(?P<end_minute>\d{2}))?\s*"
    r"(?P<end_meridiem>a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)
_EXPLICIT_START_RE = re.compile(
    r"\b(?:start(?:s|ing)?|begins?|from|clients?\s+at)\D{0,24}"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)
_EXPLICIT_END_RE = re.compile(
    r"\b(?:ends?|until|through)\D{0,16}"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)
_EXPLICIT_OPEN_ENDED_START_RE = re.compile(
    r"(?<!\d)(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*"
    r"(?P<meridiem>a\.?m\.?|p\.?m\.?)\s*(?:[-\u2013\u2014â€“â€”]|to)\s*(?:close|onward)\b",
    re.IGNORECASE,
)
_LOGGER = logging.getLogger(__name__)
_CITY_REQUEST_RETRY_DELAY_SECONDS = 1.0
_WINDOWS_WSAECONNRESET = 10054

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
                response = _fetch_city_date_with_retry(
                    fetch_json,
                    SEARCH_URL,
                    body=json.dumps(_request_payload(target, city)).encode("utf-8"),
                    headers=_api_headers(),
                    context=key,
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


def _fetch_city_date_with_retry(
    fetch_json: Callable[..., Any],
    url: str,
    *,
    body: bytes,
    headers: dict[str, str],
    context: str,
) -> Any:
    try:
        return fetch_json(url, body=body, headers=headers)
    except URLError as first_error:
        if not _is_windows_connection_reset(first_error):
            raise

        first_timestamp = _utc_timestamp()
        _LOGGER.warning(
            "allevents_city_request_connection_reset context=%s timestamp=%s "
            "retry_in_seconds=%s error=%r",
            context,
            first_timestamp,
            _CITY_REQUEST_RETRY_DELAY_SECONDS,
            first_error,
            exc_info=True,
        )
        time.sleep(_CITY_REQUEST_RETRY_DELAY_SECONDS)
        try:
            response = fetch_json(url, body=body, headers=headers)
        except Exception as second_error:
            second_timestamp = _utc_timestamp()
            second_error.add_note(
                "AllEvents city/date request retry failed; "
                f"context={context}; first_attempt_timestamp={first_timestamp}; "
                f"first_error={first_error!r}; second_attempt_timestamp={second_timestamp}"
            )
            _LOGGER.error(
                "allevents_city_request_connection_reset_retry_failed context=%s "
                "first_timestamp=%s second_timestamp=%s first_error=%r second_error=%r",
                context,
                first_timestamp,
                second_timestamp,
                first_error,
                second_error,
                exc_info=True,
            )
            raise

        _LOGGER.warning(
            "allevents_city_request_connection_reset_recovered context=%s "
            "first_failure_timestamp=%s",
            context,
            first_timestamp,
        )
        return response


def _is_windows_connection_reset(error: URLError) -> bool:
    pending: list[BaseException] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if (
            getattr(current, "winerror", None) == _WINDOWS_WSAECONNRESET
            or getattr(current, "errno", None) == _WINDOWS_WSAECONNRESET
        ):
            return True
        reason = getattr(current, "reason", None)
        if isinstance(reason, BaseException):
            pending.append(reason)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    return False


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _build_session_fetcher() -> Callable[..., Any]:
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    bootstrap_request = urllib.request.Request(BOOTSTRAP_URL, headers=_bootstrap_headers())
    with opener.open(bootstrap_request, timeout=30) as response:
        response.read()

    def fetch_json(url: str, *, body: bytes, headers: dict[str, str]) -> Any:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with opener.open(request, timeout=30) as response:
            return _decode_api_response(response)

    return fetch_json


def _decode_api_response(response: Any) -> Any:
    status = getattr(response, "status", None)
    if status is None:
        status = response.getcode()
    content_type = response.headers.get_content_type().casefold()
    charset = response.headers.get_content_charset() or "utf-8"
    text = response.read().decode(charset, errors="replace")
    cleaned = text.lstrip("\ufeff \t\r\n")

    if content_type != "application/json" and not content_type.endswith("+json"):
        prefix = _response_prefix(cleaned)
        if cleaned.casefold().startswith("not available at this moment"):
            reason = "AllEvents session/API rejection"
        else:
            reason = "AllEvents returned unexpected response media type"
        raise RuntimeError(
            f"{reason}: HTTP {status}; Content-Type {content_type!r}; "
            f"response prefix: {prefix!r}"
        )

    return _decode_api_json(
        text,
        status=status,
        content_type=content_type,
    )


def _decode_api_json(
    text: str,
    *,
    status: Any | None = None,
    content_type: str | None = None,
) -> Any:
    cleaned = text.lstrip("\ufeff \t\r\n")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        prefix = _response_prefix(cleaned)
        context = ""
        if status is not None and content_type is not None:
            context = f"HTTP {status}; Content-Type {content_type!r}; "
        raise RuntimeError(
            f"AllEvents returned non-JSON response: {context}response prefix: {prefix!r}"
        ) from exc


def _response_prefix(text: str) -> str:
    return text[:160].replace("\r", "\\r").replace("\n", "\\n")


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
    if not title or not source_id or not url:
        return None

    explicit_times = _explicit_description_times(row)
    if explicit_times is not None:
        start, end = explicit_times
        time_reason = end_reason = "description_explicit_time_range"
    else:
        explicit_start = _explicit_open_ended_description_start(row)
        if explicit_start is not None:
            start = explicit_start
            end = None
            time_reason = end_reason = "description_explicit_open_ended_start"
        else:
            start, time_reason = _api_datetime(row, "start_time", title)
            if start is None:
                return None
            end, end_reason = _api_datetime(
                row,
                "end_time",
                title,
                force_wall_clock=time_reason == "wall_clock_epoch_repaired",
            )

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
        "source_start_timestamp": int_or_none(row.get("start_time")),
        "source_end_timestamp": int_or_none(row.get("end_time")),
        "source_display_time": _clean(row.get("app_display_time") or row.get("start_time_display")),
        "recurring_event_details": row.get("recurring_event_details"),
        "source_time_reason": time_reason if time_reason == end_reason else f"start={time_reason};end={end_reason}",
    }
    return {key: value for key, value in event.items() if value not in (None, "", [], {})}


def _explicit_description_times(row: dict[str, Any]) -> tuple[datetime, datetime] | None:
    description = _clean_description(row.get("description")) or ""
    if not description or _OVERNIGHT_CUE_RE.search(description):
        return None

    range_match = _EXPLICIT_RANGE_RE.search(description)
    if range_match and re.search(r"\bpre[ -]?show\b", description[max(0, range_match.start() - 100):range_match.end() + 100], re.IGNORECASE):
        return None
    start_parts: tuple[int, int, str] | None = None
    end_parts: tuple[int, int, str] | None = None
    if range_match:
        start_parts = (
            int(range_match.group("start_hour")),
            int(range_match.group("start_minute") or 0),
            range_match.group("start_meridiem"),
        )
        end_parts = (
            int(range_match.group("end_hour")),
            int(range_match.group("end_minute") or 0),
            range_match.group("end_meridiem"),
        )
    else:
        start_match = _EXPLICIT_START_RE.search(description)
        end_match = _EXPLICIT_END_RE.search(description)
        if not start_match or not end_match:
            return None
        start_parts = (
            int(start_match.group("hour")),
            int(start_match.group("minute") or 0),
            start_match.group("meridiem"),
        )
        end_parts = (
            int(end_match.group("hour")),
            int(end_match.group("minute") or 0),
            end_match.group("meridiem"),
        )

    try:
        stamp = int(str(row.get("start_time")))
    except (TypeError, ValueError):
        return None
    offset = _timezone_offset(row.get("timezone"), stamp)
    event_date = datetime.fromtimestamp(stamp, timezone.utc).date()
    start = datetime.combine(event_date, datetime.min.time(), tzinfo=offset).replace(
        hour=_hour24(start_parts[0], start_parts[2]),
        minute=start_parts[1],
    )
    end = datetime.combine(event_date, datetime.min.time(), tzinfo=offset).replace(
        hour=_hour24(end_parts[0], end_parts[2]),
        minute=end_parts[1],
    )
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _explicit_open_ended_description_start(row: dict[str, Any]) -> datetime | None:
    description = _clean_description(row.get("description")) or ""
    if not description or _OVERNIGHT_CUE_RE.search(description):
        return None
    match = _EXPLICIT_OPEN_ENDED_START_RE.search(description)
    if not match:
        return None
    try:
        stamp = int(str(row.get("start_time")))
    except (TypeError, ValueError):
        return None
    offset = _timezone_offset(row.get("timezone"), stamp)
    event_date = datetime.fromtimestamp(stamp, timezone.utc).date()
    return datetime.combine(event_date, datetime.min.time(), tzinfo=offset).replace(
        hour=_hour24(int(match.group("hour")), match.group("meridiem")),
        minute=int(match.group("minute") or 0),
    )


def _hour24(hour: int, meridiem: str) -> int:
    if not 1 <= hour <= 12:
        raise ValueError(f"invalid 12-hour clock value: {hour}")
    normalized = meridiem.casefold().replace(".", "")
    if normalized == "am":
        return 0 if hour == 12 else hour
    return 12 if hour == 12 else hour + 12


def int_or_none(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _api_datetime(
    row: dict[str, Any],
    field: str,
    title: str,
    *,
    force_wall_clock: bool = False,
) -> tuple[datetime | None, str]:
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

    if force_wall_clock or _date_only_display_with_offset(row) or _is_wall_clock_epoch(
        utc_instant,
        local_instant,
        offset,
        evidence,
    ):
        wall_clock = utc_instant.replace(tzinfo=offset)
        reason = "date_only_display_wall_clock_repaired" if _date_only_display_with_offset(row) else "wall_clock_epoch_repaired"
        return wall_clock, reason
    return local_instant, "utc_epoch_converted"


def _date_only_display_with_offset(row: dict[str, Any]) -> bool:
    """Detect API rows whose epoch stores local wall time rather than a UTC instant.

    AllEvents' date-only cards omit an authored display time while retaining an
    explicit numeric timezone. In that payload form the epoch is the local wall
    clock encoded as UTC. Rows with an AM/PM display remain ordinary UTC epochs.
    """
    display = _clean(row.get("app_display_time") or row.get("start_time_display"))
    if not display or re.search(r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b", display, re.IGNORECASE):
        return False
    return bool(_OFFSET_RE.match(_clean(row.get("timezone"))))


def _is_wall_clock_epoch(
    utc_instant: datetime,
    local_instant: datetime,
    offset: tzinfo,
    evidence: str,
) -> bool:
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
