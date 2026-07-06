"""Known source adapter registry.

Attempt_20 formalizes this module as the stable adapter manifest used by
status tooling and source-agnostic pipeline runners.

The registry tracks source identity, implementation package, status, and
fixture locations only. Parsing and normalization remain inside each source
adapter package.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from adapters.contract import AdapterManifest


@dataclass(frozen=True)
class AdapterInfo(AdapterManifest):
    """Backward-compatible alias for one supported source adapter."""


AVAILABLE_ADAPTERS: dict[str, AdapterInfo] = {
    "VisitTriCities": AdapterInfo(
        source_name="VisitTriCities",
        fixture_path=Path("fixtures/visit_tricities/normalized_events.json"),
        raw_fixture_path=Path("fixtures/visit_tricities/raw_response.json"),
        adapter_package="adapters.visit_tricities",
        status="active",
        notes="Algolia-backed event source.",
    ),
    "LegacyUnifiedCSV": AdapterInfo(
        source_name="LegacyUnifiedCSV",
        fixture_path=Path("fixtures/legacy/normalized_events.json"),
        raw_fixture_path=None,
        adapter_package="tools.import_legacy_unified_events",
        status="migration_bridge",
        notes="Bridge for historic unified_events.csv output.",
    ),
    "RichlandLibrary": AdapterInfo(
        source_name="RichlandLibrary",
        fixture_path=Path("fixtures/richland_library/normalized_events.json"),
        raw_fixture_path=Path("fixtures/richland_library/raw_events.html"),
        adapter_package="adapters.richland_library",
        status="active",
        notes="LibCal/Springshare-backed HTML fragment source.",
    ),
    "MidColumbiaLibraries": AdapterInfo(
        source_name="MidColumbiaLibraries",
        fixture_path=Path("fixtures/mid_columbia_libraries/normalized_events.json"),
        raw_fixture_path=Path("fixtures/mid_columbia_libraries/raw_events.html"),
        adapter_package="adapters.mid_columbia_libraries",
        status="active",
        notes="Saved HTML listing parser.",
    ),
    "TriCityVibe": AdapterInfo(
        source_name="TriCityVibe",
        fixture_path=Path("fixtures/tricity_vibe/normalized_events.json"),
        raw_fixture_path=Path("fixtures/tricity_vibe/raw_events.html"),
        adapter_package="adapters.tricity_vibe",
        status="active",
        notes="WordPress-rendered saved HTML event listing parser.",
    ),
}


def get_adapter(source_name: str) -> AdapterInfo:
    """Return adapter metadata for a known source."""
    try:
        return AVAILABLE_ADAPTERS[source_name]
    except KeyError as exc:
        known = ", ".join(sorted(AVAILABLE_ADAPTERS))
        raise KeyError(f"Unknown source adapter: {source_name}. Known adapters: {known}") from exc


def list_source_names() -> list[str]:
    """Return known source names in stable sorted order."""
    return sorted(AVAILABLE_ADAPTERS)


def list_active_adapters() -> list[AdapterInfo]:
    """Return adapters that should participate in normal fixture-backed runs."""
    return [adapter for adapter in AVAILABLE_ADAPTERS.values() if adapter.status == "active"]
