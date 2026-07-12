from pathlib import Path

import pytest

from adapters.registry import SourceRegistry


def test_registry_loads_enabled_sources_in_priority_order() -> None:
    registry = SourceRegistry.load()

    names = registry.names(enabled_only=True)

    assert names[:2] == ["VisitTriCities", "TriCityVibe"]
    assert "AllEvents" in names
    assert names.index("AllEvents") < names.index("LegacyUnifiedCSV")
    assert "RichlandActiveCommunities" not in names


def test_allevents_is_active_and_active_communities_remains_planned() -> None:
    registry = SourceRegistry.load()

    allevents = registry.get("AllEvents")
    active_communities = registry.get("RichlandActiveCommunities")

    assert allevents.status == "active"
    assert allevents.enabled
    assert allevents.raw_fixture_path == Path("fixtures/allevents/raw_pages.json")
    assert active_communities.status == "planned"
    assert not active_communities.enabled


def test_registry_rejects_duplicate_source_names(tmp_path: Path) -> None:
    path = tmp_path / "sources.json"
    path.write_text(
        '{"sources": ['
        '{"source_name":"A","adapter_package":"a","status":"active","fixture_path":"a.json"},'
        '{"source_name":"A","adapter_package":"b","status":"active","fixture_path":"b.json"}'
        ']}'
    )

    with pytest.raises(ValueError, match="duplicate source registry entry"):
        SourceRegistry.load(path)
