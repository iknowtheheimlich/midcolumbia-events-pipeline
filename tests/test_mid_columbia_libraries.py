from __future__ import annotations

from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture
from adapters.mid_columbia_libraries.parser import (
    LinkToken,
    parse_listing_tokens,
    parse_meta_line,
    parse_time_range,
)
from src.pipeline import SourceBatch, run_pipeline


def test_mid_columbia_libraries_normalized_fixture_shape() -> None:
    events = load_json_fixture(Path("fixtures/mid_columbia_libraries/normalized_events.json"))

    assert len(events) == 6
    assert all(event["source"] == "MidColumbiaLibraries" for event in events)
    assert all(event.get("title") for event in events)
    assert all(event.get("start_date") for event in events)
    assert all(event.get("url") for event in events)
    assert any(event["venue"] == "Mid-Columbia Library (Pasco)" for event in events)
    assert any(event["category"] == "Branch Closure" for event in events)


def test_mid_columbia_libraries_pipeline_counts() -> None:
    events = load_json_fixture(Path("fixtures/mid_columbia_libraries/normalized_events.json"))
    result = run_pipeline([SourceBatch("MidColumbiaLibraries", events)], deduplicate=True)

    assert result.counts == {
        "all_events": 6,
        "publisher_ready_events": 6,
        "recurrence_review_events": 0,
        "deduplicated_publisher_ready_events": 6,
        "duplicate_groups": 0,
        "skipped_low_quality_dedupe": 0,
    }


def test_mid_columbia_libraries_parser_handles_listing_tokens() -> None:
    tokens = [
        "Jul 5 Sun",
        LinkToken("Coffee and Conversation", "/events/coffee-and-conversation"),
        "1:00 - 3:00pm",
        "Device help and reading recommendations.",
        "Pasco Adult Program Adults",
        "Jul 6 Mon",
        LinkToken("LEGO Club", "/events/lego-club"),
        "4:00 - 5:00pm",
        "Creative building experience.",
        "West Pasco Elementary Program 6-12",
    ]

    events = parse_listing_tokens(tokens, year=2026)

    assert len(events) == 2
    assert events[0]["start_date"] == "2026-07-05"
    assert events[0]["start_time"] == "13:00"
    assert events[0]["end_time"] == "15:00"
    assert events[0]["venue"] == "Mid-Columbia Library (Pasco)"
    assert events[1]["city"] == "Pasco"
    assert events[1]["source_branch"] == "West Pasco"


def test_mid_columbia_libraries_time_and_meta_parsing() -> None:
    assert parse_time_range("10:30 - 11:30am") == ("10:30", "11:30")
    assert parse_time_range("4:00 - 5:00pm") == ("16:00", "17:00")
    assert parse_time_range("10:00am") == ("10:00", None)
    assert parse_meta_line("West Richland Storytime 0-5") == ("West Richland", "Storytime", "0-5")
