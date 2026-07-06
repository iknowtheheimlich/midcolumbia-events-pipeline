"""Source harvesters for raw and normalized fixture generation.

Attempt_22_Harvest_Infrastructure

This module is deliberately infrastructure-only. It fetches raw source payloads,
regenerates normalized fixtures through existing adapter parsers, and leaves the
canonical event schema, publisher, resolver, and deduplication logic alone.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from adapters.registry import AdapterInfo


@dataclass(frozen=True)
class HarvestResult:
    """One source harvest/regeneration result."""

    source_name: str
    raw_fixture_path: Path | None
    normalized_fixture_path: Path
    raw_count: int | None
    normalized_count: int


@dataclass(frozen=True)
class HarvestOptions:
    """Runtime options shared by source harvesters."""

    fetch: bool = True
    regenerate: bool = True
    months: int = 2
    legacy_input: Path | None = None


Fetcher = Callable[[AdapterInfo, HarvestOptions], HarvestResult]


RAW_FIXTURE_PATHS: dict[str, Path] = {
    "VisitTriCities": Path("fixtures/visit_tricities/raw_payload.json"),
    "RichlandLibrary": Path("fixtures/richland_library/raw_monthly.html"),
    "MidColumbiaLibraries": Path("fixtures/mcl/raw_events.html"),
    "TriCityVibe": Path("fixtures/tricityvibe/raw_events.html"),
}


FETCHERS: dict[str, Fetcher] = {
    "VisitTriCities": lambda adapter, options: harvest_visit_tricities(adapter, options),
    "RichlandLibrary": lambda adapter, options: harvest_richland_library(adapter, options),
    "MidColumbiaLibraries": lambda adapter, options: harvest_mid_columbia_libraries(adapter, options),
    "TriCityVibe": lambda adapter, options: harvest_tricity_vibe(adapter, options),
    "LegacyUnifiedCSV": lambda adapter, options: harvest_legacy_unified_csv(adapter, options),
}


def harvest_adapter(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    """Harvest/regenerate one registered adapter."""
    try:
        fetcher = FETCHERS[adapter.source_name]
    except KeyError as exc:
        known = ", ".join(sorted(FETCHERS))
        raise KeyError(f"No harvester registered for {adapter.source_name}. Known harvesters: {known}") from exc
    return fetcher(adapter, options)


def harvest_visit_tricities(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    """Fetch Visit Tri-Cities Algolia payload and regenerate its normalized fixture."""
    from adapters.visit_tricities.adapter import parse_visit_tricities_payload
    from adapters.visit_tricities.config import (
        ALGOLIA_API_KEY,
        ALGOLIA_APP_ID,
        ALGOLIA_EVENT_FILTERS,
        ALGOLIA_INDEX_NAME,
        ALGOLIA_MULTI_QUERY_URL,
    )

    raw_path = RAW_FIXTURE_PATHS[adapter.source_name]
    if options.fetch:
        payload = {
            "requests": [
                {
                    "indexName": ALGOLIA_INDEX_NAME,
                    "params": urllib.parse.urlencode(
                        {
                            "hitsPerPage": 500,
                            "page": 0,
                            "filters": ALGOLIA_EVENT_FILTERS,
                        }
                    ),
                }
            ]
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Algolia-API-Key": ALGOLIA_API_KEY,
            "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        }
        raw_payload = request_json(ALGOLIA_MULTI_QUERY_URL, body=body, headers=headers)
        save_json_fixture(raw_path, raw_payload)
    else:
        raw_payload = load_json_fixture(raw_path)

    events = parse_visit_tricities_payload(raw_payload)
    if options.regenerate:
        save_json_fixture(adapter.fixture_path, events)
    return HarvestResult(adapter.source_name, raw_path, adapter.fixture_path, count_raw(raw_payload), len(events))


def harvest_richland_library(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    """Fetch Richland Library LibCal monthly fragments and regenerate fixture."""
    from adapters.richland_library.config import CALENDAR_CONTEXT, CALENDAR_ID, MONTHLY_ENDPOINT
    from adapters.richland_library.parser import parse_monthly_html

    raw_path = RAW_FIXTURE_PATHS[adapter.source_name]
    if options.fetch:
        fragments: list[str] = []
        for target in month_starts(options.months):
            params = urllib.parse.urlencode(
                {
                    "cid": CALENDAR_ID,
                    "cal_id": CALENDAR_ID,
                    "ct": CALENDAR_CONTEXT,
                    "m": target.month,
                    "y": target.year,
                    "month": target.month,
                    "year": target.year,
                }
            )
            fragments.append(request_text(f"{MONTHLY_ENDPOINT}?{params}"))
        raw_text = "\n".join(fragments)
        write_text_fixture(raw_path, raw_text)
    else:
        raw_text = raw_path.read_text(encoding="utf-8")

    events = parse_monthly_html(raw_text)
    if options.regenerate:
        save_json_fixture(adapter.fixture_path, events)
    return HarvestResult(adapter.source_name, raw_path, adapter.fixture_path, None, len(events))


def harvest_mid_columbia_libraries(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    """Fetch Mid-Columbia Libraries listing page and regenerate fixture."""
    from adapters.mid_columbia_libraries.config import EVENTS_URL
    from adapters.mid_columbia_libraries.parser import parse_listing_html

    raw_path = RAW_FIXTURE_PATHS[adapter.source_name]
    if options.fetch:
        raw_text = request_text(EVENTS_URL)
        write_text_fixture(raw_path, raw_text)
    else:
        raw_text = raw_path.read_text(encoding="utf-8")

    events = parse_listing_html(raw_text)
    if options.regenerate:
        save_json_fixture(adapter.fixture_path, events)
    return HarvestResult(adapter.source_name, raw_path, adapter.fixture_path, None, len(events))


def harvest_tricity_vibe(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    """Fetch Tri-City Vibe listing page and regenerate fixture when its adapter exists."""
    raw_path = RAW_FIXTURE_PATHS[adapter.source_name]

    try:
        from adapters.tricityvibe.config import EVENTS_URL  # type: ignore[import-not-found]
        from adapters.tricityvibe.parser import parse_listing_html  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "TriCityVibe is registered, but adapters.tricityvibe is not available in this checkout. "
            "Pull the Attempt_21 adapter files before harvesting this source."
        ) from exc

    if options.fetch:
        raw_text = request_text(EVENTS_URL)
        write_text_fixture(raw_path, raw_text)
    else:
        raw_text = raw_path.read_text(encoding="utf-8")

    events = parse_listing_html(raw_text)
    if options.regenerate:
        save_json_fixture(adapter.fixture_path, events)
    return HarvestResult(adapter.source_name, raw_path, adapter.fixture_path, None, len(events))


def harvest_legacy_unified_csv(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    """Regenerate the legacy bridge fixture from a supplied CSV path."""
    if not options.legacy_input:
        events = load_json_fixture(adapter.fixture_path)
        if not isinstance(events, list):
            raise TypeError(f"legacy normalized fixture must be a list: {adapter.fixture_path}")
        return HarvestResult(adapter.source_name, None, adapter.fixture_path, None, len(events))

    from tools.import_legacy_unified_events import read_legacy_csv

    events = read_legacy_csv(options.legacy_input)
    if options.regenerate:
        save_json_fixture(adapter.fixture_path, events)
    return HarvestResult(adapter.source_name, options.legacy_input, adapter.fixture_path, len(events), len(events))


def month_starts(count: int) -> list[date]:
    """Return first day of the current month and following months."""
    today = date.today().replace(day=1)
    months: list[date] = []
    cursor = today
    for _ in range(max(1, count)):
        months.append(cursor)
        cursor = add_month(cursor)
    return months


def add_month(value: date) -> date:
    """Return first day of the month after value."""
    next_month = (value.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month


def request_json(url: str, *, body: bytes | None = None, headers: dict[str, str] | None = None) -> Any:
    """Fetch JSON with stdlib urllib so the project keeps zero new runtime deps."""
    request = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - controlled source URLs
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def request_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    """Fetch text with stdlib urllib so the project keeps zero new runtime deps."""
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "midcolumbia-events-pipeline/Attempt_22"})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - controlled source URLs
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def write_text_fixture(path: Path, content: str) -> None:
    """Write a deterministic UTF-8 text fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def count_raw(payload: Any) -> int | None:
    """Best-effort raw event count for harvest reporting."""
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("hits"), list):
            return len(payload["hits"])
        results = payload.get("results")
        if isinstance(results, list):
            return sum(len(item.get("hits", [])) for item in results if isinstance(item, dict))
    return None
