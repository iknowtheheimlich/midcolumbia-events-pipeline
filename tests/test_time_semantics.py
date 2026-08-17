from src.pipeline import SourceBatch, run_pipeline
from src.publishing_contract import format_compact_range
from src.time_semantics import enrich_event_time_semantics


def _event(**overrides):
    event = {
        "title": "Test Event",
        "start_date": "2026-07-18",
        "end_date": "2026-07-18",
        "start_time": "18:00",
        "end_time": "23:59",
        "venue": "Test Venue",
        "city": "Kennewick",
        "url": "https://example.org/event",
        "source": "VisitTriCities",
    }
    event.update(overrides)
    return event


def test_synthetic_end_of_day_is_removed() -> None:
    enriched = enrich_event_time_semantics(_event())

    assert enriched["start_time"] == "18:00"
    assert enriched["end_time"] is None
    assert enriched["all_day"] is False
    assert enriched["intelligence"]["time_semantics"]["reason"] == "synthetic_end_of_day_removed"
    assert format_compact_range(enriched["start_time"], enriched["end_time"]) == "6p"


def test_legacy_allevents_midnight_date_only_becomes_all_day() -> None:
    enriched = enrich_event_time_semantics(
        _event(source="AllEvents", start_time="00:00", end_time=None)
    )

    assert enriched["all_day"] is True
    assert enriched["start_time"] == "All day"
    assert enriched["end_time"] is None
    assert format_compact_range(enriched["start_time"], enriched["end_time"]) == "All day"


def test_explicit_all_day_marker_replaces_clock_values() -> None:
    enriched = enrich_event_time_semantics(_event(all_day=True))

    assert enriched["all_day"] is True
    assert enriched["start_time"] == "All day"
    assert enriched["end_time"] is None


def test_legitimate_midnight_start_is_preserved() -> None:
    enriched = enrich_event_time_semantics(
        _event(start_time="00:00", end_time="02:00", source="TriCityVibe")
    )

    assert enriched["all_day"] is False
    assert enriched["start_time"] == "00:00"
    assert enriched["end_time"] == "02:00"
    assert format_compact_range(enriched["start_time"], enriched["end_time"]) == "12-2a"


def test_identical_end_time_is_removed() -> None:
    enriched = enrich_event_time_semantics(_event(start_time="17:00", end_time="17:00"))

    assert enriched["start_time"] == "17:00"
    assert enriched["end_time"] is None
    assert enriched["intelligence"]["time_semantics"]["reason"] == "identical_end_removed"


def test_pipeline_time_semantics_remains_opt_in() -> None:
    batch = SourceBatch(source_name="VisitTriCities", events=[_event()])

    legacy = run_pipeline([batch])
    enriched = run_pipeline([batch], enrich_time_semantics=True)

    assert legacy.all_events[0]["end_time"] == "23:59"
    assert enriched.all_events[0]["end_time"] is None
    assert "time_semantics" in enriched.all_events[0]["intelligence"]


def test_allevents_multiday_local_midnight_range_has_unknown_occurrence_time() -> None:
    event = _event(
        source="AllEvents", start_date="2026-08-20", end_date="2026-08-23",
        start_time="07:00", end_time="07:59", source_start_timestamp=1787209200,
        source_end_timestamp=1787471940, source_timezone="-07:00",
    )
    result = run_pipeline(
        [SourceBatch("AllEvents", [event])], publication_week_start=__import__("datetime").date(2026, 8, 17),
        enrich_time_semantics=True,
    )
    assert len(result.all_events) == 4
    assert {(row["start_time"], row["end_time"]) for row in result.all_events} == {(None, None)}
    assert all(row["time_unknown"] for row in result.all_events)


def test_date_boundary_sentinels_are_not_rendered_as_midnight() -> None:
    enriched = enrich_event_time_semantics(_event(start_time="00:00", end_time="23:59"))
    assert enriched["start_time"] is None
    assert enriched["end_time"] is None
    assert enriched["time_unknown"] is True
