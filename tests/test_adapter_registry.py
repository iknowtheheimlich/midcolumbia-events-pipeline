from __future__ import annotations

from adapters.registry import AVAILABLE_ADAPTERS, get_adapter, list_source_names


def test_adapter_registry_contains_active_sources() -> None:
    assert list_source_names() == ["LegacyUnifiedCSV", "RichlandLibrary", "VisitTriCities"]

    assert AVAILABLE_ADAPTERS["VisitTriCities"].status == "active"
    assert AVAILABLE_ADAPTERS["RichlandLibrary"].status == "active"
    assert AVAILABLE_ADAPTERS["LegacyUnifiedCSV"].status == "migration_bridge"


def test_get_adapter_returns_metadata() -> None:
    adapter = get_adapter("RichlandLibrary")

    assert adapter.source_name == "RichlandLibrary"
    assert str(adapter.fixture_path) == "fixtures\\richland_library\\normalized_events.json" or str(adapter.fixture_path) == "fixtures/richland_library/normalized_events.json"
