"""Harvest infrastructure for raw and normalized source fixtures.

Attempt_22_Harvest_Infrastructure

This module owns source fetching and fixture regeneration only. It deliberately
leaves the canonical event schema, publisher, resolver, recurrence classifier,
and deduplication logic untouched.
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
from adapters.contract import CanonicalEvent
from adapters.registry import AdapterInfo


@dataclass(frozen=True)
class HarvestOptions:
    """Runtime controls for one harvest run."""

    fetch_raw: bool = True
    regenerate_normalized: bool = True
    months: int = 2
    legacy_input: Path | None = None


@dataclass(frozen=True)
class HarvestResult:
    """Summary for one harvested source."""

    source_name: str
    raw_fixture_path: Path | None
    normalized_fixture_path: Path
    raw_count: int | None
    normalized_count: int
    reused_normalized: bool = False
    error: str | None = None


@dataclass(frozen=True)
class Harvester:
    """Fetcher/normalizer pair for one adapter."""

    source_name: str
    fetch_raw: Callable[[AdapterInfo, HarvestOptions], Any]
    normalize: Callable[[Any], list[CanonicalEvent]]

    def harvest(self, adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
        """Fetch/read raw fixture, regenerate normalized fixture, and report counts."""
        if should_reuse_normalized(adapter, options):
            return reuse_normalized_result(adapter)

        try:
            raw_payload = self._load_or_fetch_raw(adapter, options)
            normalized_events = self.normalize(raw_payload)
        except Exception as exc:
            if adapter.fixture_path.exists():
                return reuse_normalized_result(adapter, error=f"{type(exc).__name__}: {exc}")
            raise

        if options.regenerate_normalized:
            save_json_fixture(adapter.fixture_path, normalized_events)

        return HarvestResult(
            source_name=adapter.source_name,
            raw_fixture_path=adapter.raw_fixture_path,
            normalized_fixture_path=adapter.fixture_path,
            raw_count=count_raw(raw_payload),
            normalized_count=len(normalized_events),
        )

    def _load_or_fetch_raw(self, adapter: AdapterInfo, options: HarvestOptions) -> Any:
        if adapter.raw_fixture_path is None:
            return self.fetch_raw(adapter, options)

        if options.fetch_raw:
            raw_payload = self.fetch_raw(adapter, options)
            save_raw_fixture(adapter.raw_fixture_path, raw_payload)
            return raw_payload

        return load_raw_fixture(adapter.raw_fixture_path)


def harvest_adapter(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    """Harvest one adapter using its registered harvester."""
    harvester = get_harvester(adapter.source_name)
    return harvester.harvest(adapter, options)


def get_harvester(source_name: str) -> Harvester:
    """Return harvester for a supported source."""
    try:
        return HARVESTERS[source_name]
    except KeyError as exc:
        known = ", ".join(sorted(HARVESTERS))
        raise KeyError(f"No harvester registered for {source_name}. Known harvesters: {known}") from exc


def should_reuse_normalized(adapter: AdapterInfo, options: HarvestOptions) -> bool:
    """Return whether offline mode should preserve an existing normalized fixture."""
    if options.fetch_raw:
        return False
    if adapter.raw_fixture_path is None:
        return False
    if adapter.raw_fixture_path.exists():
        return False
    return adapter.fixture_path.exists()


def reuse_normalized_result(adapter: AdapterInfo, *, error: str | None = None) -> HarvestResult:
    """Return a harvest result that preserves the current normalized fixture."""
    normalized_events = load_normalized_fixture(adapter.fixture_path)
    return HarvestResult(
        source_name=adapter.source_name,
        raw_fixture_path=adapter.raw_fixture_path,
        normalized_fixture_path=adapter.fixture_path,
        raw_count=None,
        normalized_count=len(normalized_events),
        reused_normalized=True,
        error=error,
    )


def fetch_visit_tricities_raw(adapter: AdapterInfo, options: HarvestOptions) -> Any:
    """Fetch Visit Tri-Cities Algolia payload."""
    from adapters.visit_tricities.config import (
        ALGOLIA_API_KEY,
        ALGOLIA_APP_ID,
        ALGOLIA_EVENT_FILTERS,
        ALGOLIA_INDEX_NAME,
        ALGOLIA_MULTI_QUERY_URL,
    )

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
    headers = {
        "Content-Type": "application/json",
        "X-Algolia-API-Key": ALGOLIA_API_KEY,
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    }
    return request_json(ALGOLIA_MULTI_QUERY_URL, body=json.dumps(payload).encode("utf-8"), headers=headers)


def normalize_visit_tricities(raw_payload: Any) -> list[CanonicalEvent]:
    """Regenerate Visit Tri-Cities normalized events from raw payload."""
    from adapters.visit_tricities.adapter import parse_visit_tricities_payload

    return parse_visit_tricities_payload(raw_payload)


def fetch_richland_library_raw(adapter: AdapterInfo, options: HarvestOptions) -> str:
    """Fetch Richland Library LibCal monthly HTML fragments."""
    from adapters.richland_library.config import CALENDAR_CONTEXT, CALENDAR_ID, MONTHLY_ENDPOINT

    fragments: list[str] = []
    for target_month in month_starts(options.months):
        params = urllib.parse.urlencode(
            {
                "cal_id": CALENDAR_ID,
                "ct": CALENDAR_CONTEXT,
                "m": target_month.month,
                "y": target_month.year,
            }
        )
        fragments.append(request_text(f"{MONTHLY_ENDPOINT}?{params}"))
    return "\n".join(fragments)


def normalize_richland_library(raw_payload: Any) -> list[CanonicalEvent]:
    """Regenerate Richland Library normalized events from raw HTML."""
    from adapters.richland_library.parser import parse_monthly_html

    return parse_monthly_html(require_text(raw_payload, "RichlandLibrary raw fixture"))


def fetch_mid_columbia_libraries_raw(adapter: AdapterInfo, options: HarvestOptions) -> str:
    """Fetch Mid-Columbia Libraries events listing HTML."""
    from adapters.mid_columbia_libraries.config import EVENTS_URL

    return request_text(EVENTS_URL)


def normalize_mid_columbia_libraries(raw_payload: Any) -> list[CanonicalEvent]:
    """Regenerate Mid-Columbia Libraries normalized events from raw HTML."""
    from adapters.mid_columbia_libraries.parser import parse_listing_html

    return parse_listing_html(require_text(raw_payload, "MidColumbiaLibraries raw fixture"))


def fetch_tricity_vibe_raw(adapter: AdapterInfo, options: HarvestOptions) -> str:
    """Fetch Tri-City Vibe events listing HTML."""
    from adapters.tricity_vibe.config import EVENTS_URL

    return request_text(EVENTS_URL)


def normalize_tricity_vibe(raw_payload: Any) -> list[CanonicalEvent]:
    """Regenerate Tri-City Vibe normalized events from raw HTML."""
    from adapters.tricity_vibe.parser import parse_events_html

    return parse_events_html(require_text(raw_payload, "TriCityVibe raw fixture"))


def fetch_legacy_unified_csv_raw(adapter: AdapterInfo, options: HarvestOptions) -> list[CanonicalEvent]:
    """Read legacy CSV when supplied, otherwise reuse the existing normalized bridge fixture."""
    if options.legacy_input is None:
        return load_normalized_fixture(adapter.fixture_path)

    from tools.import_legacy_unified_events import read_legacy_csv

    return read_legacy_csv(options.legacy_input)


def normalize_legacy_unified_csv(raw_payload: Any) -> list[CanonicalEvent]:
    """Legacy bridge raw payload is already canonicalized by the importer."""
    if not isinstance(raw_payload, list):
        raise TypeError("LegacyUnifiedCSV payload must be a list of events")
    return [dict(event) for event in raw_payload if isinstance(event, dict)]


HARVESTERS: dict[str, Harvester] = {
    "VisitTriCities": Harvester("VisitTriCities", fetch_visit_tricities_raw, normalize_visit_tricities),
    "RichlandLibrary": Harvester("RichlandLibrary", fetch_richland_library_raw, normalize_richland_library),
    "MidColumbiaLibraries": Harvester(
        "MidColumbiaLibraries", fetch_mid_columbia_libraries_raw, normalize_mid_columbia_libraries
    ),
    "TriCityVibe": Harvester("TriCityVibe", fetch_tricity_vibe_raw, normalize_tricity_vibe),
    "LegacyUnifiedCSV": Harvester("LegacyUnifiedCSV", fetch_legacy_unified_csv_raw, normalize_legacy_unified_csv),
}


def month_starts(count: int) -> list[date]:
    """Return first day of current month and the following N-1 months."""
    cursor = date.today().replace(day=1)
    months: list[date] = []
    for _ in range(max(1, count)):
        months.append(cursor)
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


def request_json(url: str, *, body: bytes | None = None, headers: dict[str, str] | None = None) -> Any:
    """Fetch JSON using stdlib urllib to avoid new runtime dependencies."""
    request = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - controlled adapter URLs
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def request_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    """Fetch text using stdlib urllib to avoid new runtime dependencies."""
    request = urllib.request.Request(url, headers=headers or default_headers())
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - controlled adapter URLs
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def default_headers() -> dict[str, str]:
    """Return polite headers for public source fetches."""
    return {"User-Agent": "midcolumbia-events-pipeline/Attempt_22"}


def save_raw_fixture(path: Path, payload: Any) -> None:
    """Save raw JSON or text fixture deterministically."""
    if isinstance(payload, (dict, list)):
        save_json_fixture(path, payload)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(require_text(payload, str(path)).rstrip() + "\n", encoding="utf-8")


def load_raw_fixture(path: Path) -> Any:
    """Load raw fixture based on extension."""
    if path.suffix.lower() == ".json":
        return load_json_fixture(path)
    return path.read_text(encoding="utf-8")


def load_normalized_fixture(path: Path) -> list[CanonicalEvent]:
    """Load an existing normalized fixture as canonical event dictionaries."""
    events = load_json_fixture(path)
    if not isinstance(events, list):
        raise TypeError(f"normalized fixture must be a list: {path}")
    return [dict(event) for event in events if isinstance(event, dict)]


def require_text(value: Any, label: str) -> str:
    """Return value as text or raise a clear fixture-contract error."""
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    return value


def count_raw(payload: Any) -> int | None:
    """Best-effort raw event count for harvest reporting."""
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        hits = payload.get("hits")
        if isinstance(hits, list):
            return len(hits)
        results = payload.get("results")
        if isinstance(results, list):
            return sum(len(item.get("hits", [])) for item in results if isinstance(item, dict))
    return None
