from adapters.registry import get_adapter, list_source_names


def test_adapter_registry_contains_implemented_sources() -> None:
    assert list_source_names() == [
        "AllEvents",
        "LegacyUnifiedCSV",
        "MidColumbiaLibraries",
        "RichlandLibrary",
        "TriCityVibe",
        "VisitTriCities",
    ]


def test_get_adapter_returns_metadata() -> None:
    adapter = get_adapter("VisitTriCities")

    assert adapter.source_name == "VisitTriCities"
    assert adapter.status == "active"


def test_get_adapter_rejects_unknown_source() -> None:
    try:
        get_adapter("Nope")
    except KeyError as exc:
        assert "Unknown source adapter" in str(exc)
    else:
        raise AssertionError("expected KeyError")
