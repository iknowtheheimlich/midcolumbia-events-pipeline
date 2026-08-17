from datetime import date

import pytest

from src.notion_weekly_curation import curation_key
from src.occurrence_expansion import expand_multi_day_occurrences
from src.pipeline import SourceBatch, run_pipeline


def event(title="Camp", start="2026-08-10", end="2026-08-13", **changes):
    row = {
        "title": title, "start_date": start, "end_date": end,
        "start_time": "09:00", "end_time": "14:00",
        "venue": "Community Center", "city": "Richland",
        "source": "AllEvents", "source_event_id": "source-1",
        "url": "https://example.test/event", "description": "Four-day camp.",
        "category": "Events/Hangouts",
    }
    row.update(changes)
    return row


@pytest.mark.parametrize(("title", "start", "end", "count"), [
    ("STEAM Camp", "2026-08-10", "2026-08-13", 4),
    ("Community Champions car wash", "2026-08-11", "2026-08-12", 2),
    ("Farm City Pro Rodeo", "2026-08-12", "2026-08-15", 4),
    ("Team Policy Debate Camp", "2026-08-13", "2026-08-15", 3),
    ("Grupo Bronco", "2026-08-14", "2026-08-15", 2),
    ("Paranormal Cirque Voodoo", "2026-08-14", "2026-08-17", 3),
    ("Grandview Summer Heat", "2026-08-15", "2026-08-16", 2),
])
def test_august_regression_cohort(title, start, end, count):
    expanded = expand_multi_day_occurrences(
        [event(title, start, end)], week_start=date(2026, 8, 10)
    )
    assert len(expanded) == count
    assert all(item["source_start_date"] == start for item in expanded)
    assert all(item["source_end_date"] == end for item in expanded)


def test_august_regression_cohort_totals_twenty_occurrences():
    ranges = [
        event("STEAM Camp", "2026-08-10", "2026-08-13", source_event_id="1"),
        event("Community Champions", "2026-08-11", "2026-08-12", source_event_id="2"),
        event("Farm City Pro Rodeo", "2026-08-12", "2026-08-15", source_event_id="3"),
        event("Team Policy Debate Camp", "2026-08-13", "2026-08-15", source_event_id="4"),
        event("Grupo Bronco", "2026-08-14", "2026-08-15", source_event_id="5"),
        event("Paranormal Cirque Voodoo", "2026-08-14", "2026-08-17", source_event_id="6"),
        event("Grandview Summer Heat", "2026-08-15", "2026-08-16", source_event_id="7"),
    ]
    assert len(expand_multi_day_occurrences(ranges, week_start=date(2026, 8, 10))) == 20


def test_clips_ranges_at_both_week_boundaries():
    rows = [
        event(start="2026-08-08", end="2026-08-11", source_event_id="left"),
        event(start="2026-08-15", end="2026-08-18", source_event_id="right"),
    ]
    expanded = expand_multi_day_occurrences(rows, week_start=date(2026, 8, 10))
    assert [item["start_date"] for item in expanded] == [
        "2026-08-10", "2026-08-11", "2026-08-15", "2026-08-16"
    ]


def test_single_invalid_and_unsupported_long_ranges_preserve_existing_policy():
    rows = [
        event(start="2026-08-11", end="2026-08-11", source_event_id="single"),
        event(start="2026-08-12", end="2026-08-10", source_event_id="reverse"),
        event(start="2026-08-10", end="2026-08-20", source_event_id="long"),
    ]
    expanded = expand_multi_day_occurrences(rows, week_start=date(2026, 8, 10))
    assert len(expanded) == 3
    assert expanded[0]["start_date"] == "2026-08-11"
    assert expanded[0]["occurrence_identity"].endswith("|2026-08-11")
    assert expanded[1:] == rows[1:]


def test_preserves_time_and_uses_only_explicit_day_specific_time():
    source = event(occurrence_times={
        "2026-08-11": {"start_time": "10:30", "end_time": "15:00"}
    })
    expanded = expand_multi_day_occurrences([source], week_start=date(2026, 8, 10))
    assert [(x["start_time"], x["end_time"]) for x in expanded[:2]] == [
        ("09:00", "14:00"), ("10:30", "15:00")
    ]
    assert expanded[0]["source_time_evidence"]["start_time"] == "09:00"


def test_occurrence_identity_and_curation_keys_are_stable_and_date_specific():
    first = expand_multi_day_occurrences([event()], week_start=date(2026, 8, 10))
    second = expand_multi_day_occurrences([event()], week_start=date(2026, 8, 10))
    assert [x["occurrence_identity"] for x in first] == [x["occurrence_identity"] for x in second]
    keys = [curation_key(x, "2026-08-10") for x in first]
    assert len(keys) == len(set(keys)) == 4


def test_manual_copied_page_dates_match_canonical_repair_keys():
    grupo = event(
        "Grupo Bronco", "2026-08-15", "2026-08-15",
        source_event_id="2300029885338249",
    )
    assert curation_key(grupo, "2026-08-10") == "wc_454919e16d989cc72b854ef706fbe0f0"
    paranormal = {
        "title": "Paranormal Cirque Voodoo", "source": "AllEvents",
        "source_event_id": "2300030478036655", "venue": "Columbia Center Mall",
        "start_time": "12:30",
    }
    assert curation_key({**paranormal, "start_date": "2026-08-15"}, "2026-08-10") == "wc_9a489ae5dc22364e786a9d20c42354ed"
    assert curation_key({**paranormal, "start_date": "2026-08-16"}, "2026-08-10") == "wc_0662d8bfbe516b788062647a5989a7d6"


def test_repeated_acquisition_deduplicates_expanded_occurrences():
    result = run_pipeline(
        [SourceBatch("AllEvents", [event(), event()])], deduplicate=True,
        publication_week_start=date(2026, 8, 10),
    )
    assert len(result.publisher_ready_events) == 8
    assert len(result.deduplicated_publisher_ready_events) == 4


def test_single_day_corroboration_merges_matching_expanded_occurrence():
    corroborating = event(
        start="2026-08-11", end="2026-08-11", source="VisitTriCities",
        source_event_id="other", url="https://other.test/event",
    )
    result = run_pipeline(
        [SourceBatch("AllEvents", [event()]), SourceBatch("VisitTriCities", [corroborating])],
        deduplicate=True, resolve_cross_source_occurrences=True,
        publication_week_start=date(2026, 8, 10),
    )
    assert len(result.deduplicated_publisher_ready_events) == 4
    merged = next(x for x in result.deduplicated_publisher_ready_events if x["start_date"] == "2026-08-11")
    assert merged["duplicate_count"] == 2


def test_sibling_dates_do_not_inherit_occurrence_specific_disposition():
    from src.production_dispositions import ProductionDispositions
    policy = ProductionDispositions("mission", "2026-08-10", (), ({
        "cohort": "one day", "reason": "Captain excluded", "evidence": "reviewed",
        "selectors": [{"source": "AllEvents", "source_event_id": "source-1", "start_date": "2026-08-11"}],
    },))
    result = run_pipeline(
        [SourceBatch("AllEvents", [event()])], publication_week_start=date(2026, 8, 10),
        production_dispositions=policy,
    )
    excluded = [x for x in result.all_events if x.get("captain_disposition") == "EXCLUDE"]
    assert [x["start_date"] for x in excluded] == ["2026-08-11"]


def test_out_of_area_range_remains_out_of_area_after_expansion():
    result = run_pipeline(
        [SourceBatch("AllEvents", [event(city="Hermiston")])], enrich_geography=True,
        publication_week_start=date(2026, 8, 10),
    )
    assert len(result.all_events) == 4
    assert all(x["geo_scope"] == "OUT_OF_AREA" for x in result.all_events)


def test_exclusive_midnight_end_does_not_create_next_day_occurrence():
    source = event(start="2026-08-22", end="2026-08-23", start_time="20:00", end_time="00:00")
    source["exclusive_end_date"] = True
    expanded = expand_multi_day_occurrences([source], week_start=date(2026, 8, 17))
    assert [row["start_date"] for row in expanded] == ["2026-08-22"]
