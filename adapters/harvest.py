"""Harvest infrastructure for raw and normalized source fixtures."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from adapters.contract import CanonicalEvent
from adapters.registry import AdapterInfo

GENERATED_ROOT = Path("generated/harvest")
RICHlAND_COMPONENT_RE = re.compile(r's-lc-hp-calendar-content-(?P<id>\d+)')


@dataclass(frozen=True)
class HarvestOptions:
    fetch_raw: bool = True
    write_raw: bool = False
    write_normalized: bool = False
    months: int = 2
    legacy_input: Path | None = None


@dataclass(frozen=True)
class HarvestResult:
    source_name: str
    raw_fixture_path: Path | None
    raw_output_path: Path | None
    normalized_fixture_path: Path
    raw_count: int | None
    normalized_events: list[CanonicalEvent] = field(repr=False)
    reused_normalized: bool = False
    error: str | None = None

    @property
    def normalized_count(self) -> int:
        return len(self.normalized_events)


@dataclass(frozen=True)
class Harvester:
    source_name: str
    fetch_raw: Callable[[AdapterInfo, HarvestOptions], Any]
    normalize: Callable[[Any], list[CanonicalEvent]]

    def harvest(self, adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
        if should_reuse_normalized(adapter, options):
            return reuse_normalized_result(adapter)

        raw_output_path: Path | None = None
        try:
            raw_payload, raw_output_path = self._load_or_fetch_raw(adapter, options)
            normalized_events = self.normalize(raw_payload)
        except Exception as exc:
            if adapter.fixture_path.exists():
                return reuse_normalized_result(adapter, error=f"{type(exc).__name__}: {exc}")
            raise

        if options.write_normalized:
            save_json_fixture(adapter.fixture_path, normalized_events)

        return HarvestResult(
            source_name=adapter.source_name,
            raw_fixture_path=adapter.raw_fixture_path,
            raw_output_path=raw_output_path,
            normalized_fixture_path=adapter.fixture_path,
            raw_count=count_raw(raw_payload),
            normalized_events=normalized_events,
        )

    def _load_or_fetch_raw(self, adapter: AdapterInfo, options: HarvestOptions) -> tuple[Any, Path | None]:
        if adapter.raw_fixture_path is None:
            return self.fetch_raw(adapter, options), None
        if options.fetch_raw:
            raw_payload = self.fetch_raw(adapter, options)
            output_path = adapter.raw_fixture_path if options.write_raw else generated_raw_path(adapter)
            save_raw_fixture(output_path, raw_payload)
            return raw_payload, output_path
        return load_raw_fixture(adapter.raw_fixture_path), adapter.raw_fixture_path


def harvest_adapter(adapter: AdapterInfo, options: HarvestOptions) -> HarvestResult:
    return get_harvester(adapter.source_name).harvest(adapter, options)


def get_harvester(source_name: str) -> Harvester:
    try:
        return HARVESTERS[source_name]
    except KeyError as exc:
        known = ", ".join(sorted(HARVESTERS))
        raise KeyError(f"No harvester registered for {source_name}. Known harvesters: {known}") from exc


def generated_raw_path(adapter: AdapterInfo) -> Path:
    if adapter.raw_fixture_path is None:
        raise ValueError(f"{adapter.source_name} has no raw fixture path")
    return GENERATED_ROOT / adapter.source_name / adapter.raw_fixture_path.name


def should_reuse_normalized(adapter: AdapterInfo, options: HarvestOptions) -> bool:
    if options.fetch_raw:
        return False
    if adapter.raw_fixture_path is None:
        return False
    if adapter.raw_fixture_path.exists():
        return False
    return adapter.fixture_path.exists()


def reuse_normalized_result(adapter: AdapterInfo, *, error: str | None = None) -> HarvestResult:
    events = load_normalized_fixture(adapter.fixture_path)
    return HarvestResult(
        source_name=adapter.source_name,
        raw_fixture_path=adapter.raw_fixture_path,
        raw_output_path=None,
        normalized_fixture_path=adapter.fixture_path,
        raw_count=None,
        normalized_events=events,
        reused_normalized=True,
        error=error,
    )


def fetch_visit_tricities_raw(adapter: AdapterInfo, options: HarvestOptions) -> Any:
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
                    {"hitsPerPage": 500, "page": 0, "filters": ALGOLIA_EVENT_FILTERS}
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
    from adapters.visit_tricities.adapter import parse_visit_tricities_payload

    return parse_visit_tricities_payload(raw_payload)


def fetch_richland_library_raw(adapter: AdapterInfo, options: HarvestOptions) -> str:
    from adapters.richland_library.config import BASE_URL, CALENDAR_ID, MONTHLY_ENDPOINT

    root_html = request_text(BASE_URL, headers=default_headers())
    component_ids = sorted(set(RICHlAND_COMPONENT_RE.findall(root_html)))
    if not component_ids:
        raise RuntimeError("Richland homepage calendar component ID was not found")

    component_id = component_ids[0]
    fragments: list[str] = []
    failures: list[str] = []
    headers = {
        **default_headers(),
        "Referer": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    }

    for target_month in month_starts(options.months):
        params = urllib.parse.urlencode(
            {
                "id": component_id,
                "c": CALENDAR_ID,
                "date": target_month.isoformat(),
                "monthly": "true",
                "audience": "",
                "cats": "",
                "camps": "",
            }
        )
        url = f"{MONTHLY_ENDPOINT}?{params}"
        try:
            fragment = request_text(url, headers=headers)
            if fragment.strip():
                fragments.append(fragment)
            else:
                failures.append(f"{target_month:%Y-%m}: empty monthly response")
        except Exception as exc:
            failures.append(f"{target_month:%Y-%m}: {type(exc).__name__}: {exc}")

    if fragments:
        return "\n".join(fragments)
    raise RuntimeError("Richland LibCal fetch failed: " + " | ".join(failures))


def normalize_richland_library(raw_payload: Any) -> list[CanonicalEvent]:
    from adapters.richland_library.parser import parse_monthly_html

    return parse_monthly_html(require_text(raw_payload, "RichlandLibrary raw fixture"))


def fetch_mid_columbia_libraries_raw(adapter: AdapterInfo, options: HarvestOptions) -> str:
    from adapters.mid_columbia_libraries.config import EVENTS_URL

    return request_text(EVENTS_URL)


def normalize_mid_columbia_libraries(raw_payload: Any) -> list[CanonicalEvent]:
    from adapters.mid_columbia_libraries.parser import parse_listing_html

    return parse_listing_html(require_text(raw_payload, "MidColumbiaLibraries raw fixture"))


def fetch_tricity_vibe_raw(adapter: AdapterInfo, options: HarvestOptions) -> str:
    from adapters.tricity_vibe.config import EVENTS_URL

    return request_text(EVENTS_URL)


def normalize_tricity_vibe(raw_payload: Any) -> list[CanonicalEvent]:
    from adapters.tricity_vibe.parser import parse_events_html

    return parse_events_html(require_text(raw_payload, "TriCityVibe raw fixture"))


def fetch_legacy_unified_csv_raw(adapter: AdapterInfo, options: HarvestOptions) -> list[CanonicalEvent]:
    if options.legacy_input is None:
        return load_normalized_fixture(adapter.fixture_path)
    from tools.import_legacy_unified_events import read_legacy_csv

    return read_legacy_csv(options.legacy_input)


def normalize_legacy_unified_csv(raw_payload: Any) -> list[CanonicalEvent]:
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
    cursor = date.today().replace(day=1)
    months: list[date] = []
    for _ in range(max(1, count)):
        months.append(cursor)
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


def request_json(url: str, *, body: bytes | None = None, headers: dict[str, str] | None = None) -> Any:
    request = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def request_text(
    url: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    request = urllib.request.Request(url, data=body, headers=headers or default_headers())
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def default_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/142.0 Safari/537.36"
    }


def save_raw_fixture(path: Path, payload: Any) -> None:
    if isinstance(payload, (dict, list)):
        save_json_fixture(path, payload)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(require_text(payload, str(path)).rstrip() + "\n", encoding="utf-8")


def load_raw_fixture(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return load_json_fixture(path)
    return path.read_text(encoding="utf-8")


def load_normalized_fixture(path: Path) -> list[CanonicalEvent]:
    events = load_json_fixture(path)
    if not isinstance(events, list):
        raise TypeError(f"normalized fixture must be a list: {path}")
    return [dict(event) for event in events if isinstance(event, dict)]


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    return value


def count_raw(payload: Any) -> int | None:
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
