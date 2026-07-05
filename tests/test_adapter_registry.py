from __future__ import annotations

from adapters.registry import AVAILABLE_ADAPTERS, get_adapter, list_source_names


def test_adapter_registry_contains_active_sources() -> None:
    assert list_source_names() == [
        "LegacyUnifiedCSV",
        "MidColumbiaLibraries",
        "RichlandLibrary",
        "VisitTriCities",
    ]

    assert AVAILABLE_ADAPTERS["VisitTriCities"].status == "active"
    assert AVAILABLE_ADAPTERS["RichlandLibrary"].status == "active"
    assert AVAILABLE_ADAPTERS["MidColumbiaLibraries"].status == "active"
    assert AVAILABLE_ADAPTERS["LegacyUnifiedCSV"].status == "migration_bridge"


def test_get_adapter_returns_metadata() -> None:
    adapter = get_adapter("RichlandLibrary")

    assert adapter.source_name == "RichlandLibrary"
    assert str(adapter.fixture_path) in {
        "fixtures\\richland_library\\normalized_events.json",
        "fixtures/richland_library/normalized_events.json",
    }


def test_get_mcl_adapter_returns_metadata() -> None:
    adapter = get_adapter("MidColumbiaLibraries")

    assert adapter.source_name == "MidColumbiaLibraries"
    assert str(adapter.fixture_path) in {
        "fixtures\\mcl\\normalized_events.json",
        "fixtures/mcl/normalized_events.json",
    }