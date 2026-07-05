"""Known source adapter registry.

This module intentionally tracks source identity and fixture locations only.
Actual parsing/normalization still belongs inside each source adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdapterInfo:
    """Metadata for one supported source adapter."""

    source_name: str
    fixture_path: Path
    adapter_package: str
    status: str


AVAILABLE_ADAPTERS: dict[str, AdapterInfo] = {
    "VisitTriCities": AdapterInfo(
        source_name="VisitTriCities",
        fixture_path=Path("fixtures/visit_tricities/normalized_events.json"),
        adapter_package="adapters.visit_tricities",
        status="active",
    ),
    "LegacyUnifiedCSV": AdapterInfo(
        source_name="LegacyUnifiedCSV",
        fixture_path=Path("fixtures/legacy/normalized_events.json"),
        adapter_package="tools.import_legacy_unified_events",
        status="migration_bridge",
    ),
    "RichlandLibrary": AdapterInfo(
        source_name="RichlandLibrary",
        fixture_path=Path("fixtures/richland_library/normalized_events.json"),
        adapter_package="adapters.richland_library",
        status="active",
    ),
    "MidColumbiaLibraries": AdapterInfo(
        source_name="MidColumbiaLibraries",
        fixture_path=Path("fixtures/mcl/normalized_events.json"),
        adapter_package="adapters.mcl",
        status="active",
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

