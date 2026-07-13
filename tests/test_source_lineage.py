from src.occurrence_resolution import resolve_occurrences
from src.source_lineage import enrich_event_source_lineage


def event(**overrides):
    values = {
        "title": "Family Movies of the 1990s",
        "venue": "Richland Public Library",
        "city": "Richland",
        "start_date": "2026-07-18",
        "start_time": "11:00",
        "source": "AllEvents",
        "url": "https://allevents.in/richland/family-movies/200030000000001",
    }
    values.update(overrides)
    return values


def test_allevents_library_copy_records_origin_and_discovery_separately() -> None:
    enriched = enrich_event_source_lineage(event())

    assert enriched["origin_source"] == "RichlandLibrary"
    assert enriched["discovery_source"] == "AllEvents"
    assert enriched["is_syndicated"] is True
    assert enriched["intelligence"]["source_lineage"]["reason"] == (
        "syndicated_richland_library_via_allevents"
    )


def test_unrecognized_allevents_record_remains_native_to_aggregator() -> None:
    enriched = enrich_event_source_lineage(event(venue="Columbia Park"))

    assert enriched["origin_source"] == "AllEvents"
    assert enriched["discovery_source"] == "AllEvents"
    assert enriched["is_syndicated"] is False


def test_native_library_record_wins_over_syndicated_copy() -> None:
    result = resolve_occurrences(
        [
            event(title="Family Movies ofFamily Movies of the 1990s"),
            event(
                title="Family Movies of the 1990s",
                source="RichlandLibrary",
                url="https://myrichlandlibrary.libcal.com/event/12345",
            ),
        ]
    )

    assert len(result.events) == 1
    resolved = result.events[0]
    assert resolved["source"] == "RichlandLibrary"
    assert resolved["title"] == "Family Movies of the 1990s"


def test_syndicated_copy_is_not_independent_corroboration() -> None:
    result = resolve_occurrences(
        [
            event(),
            event(
                source="RichlandLibrary",
                url="https://myrichlandlibrary.libcal.com/event/12345",
            ),
        ]
    )

    resolved = result.events[0]
    assert resolved["duplicate_sources"] == ["AllEvents", "RichlandLibrary"]
    assert resolved["origin_sources"] == ["RichlandLibrary"]
    assert resolved["corroborating_sources"] == ["RichlandLibrary"]
    assert resolved["independent_source_count"] == 1
    assert all("origin_source" in row for row in resolved["occurrence_provenance"])
