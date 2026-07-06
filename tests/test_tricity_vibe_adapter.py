from __future__ import annotations

import json
from pathlib import Path

from adapters.registry import get_adapter, list_source_names
from adapters.tricity_vibe.parser import (
    parse_city,
    parse_events_html,
    parse_time_range,
)


FIXTURE_PATH = Path("fixtures/tricity_vibe/raw_events.html")
NORMALIZED_PATH = Path("fixtures/tricity_vibe/normalized_events.json")


def test_tricity_vibe_registered() -> None:
    adapter = get_adapter("TriCityVibe")

    assert adapter.source_name == "TriCityVibe"
    assert adapter.status == "active"
    assert adapter.fixture_path == NORMALIZED_PATH
    assert "TriCityVibe" in list_source_names()


def test_parse_tricity_vibe_fixture() -> None:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    events = parse_events_html(html)

    assert len(events) == 4
    assert events[0]["title"] == "From The Ashes performing at Irrigon Outdoor Music Festival"
    assert events[0]["venue"] == "Irrigon Marina"
    assert events[0]["city"] == "Irrigon"
    assert events[0]["start_date"] == "2026-07-06"
    assert events[0]["start_time"] == "19:00"
    assert events[0]["end_time"] == "20:30"
    assert events[0]["source"] == "TriCityVibe"


def test_parse_tricity_vibe_stops_before_past_events() -> None:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    events = parse_events_html(html)
    titles = {event["title"] for event in events}

    assert "Past Event Should Not Parse" not in titles


def test_tricity_vibe_time_parsing_handles_ranges_and_typos() -> None:
    assert parse_time_range("7 - 8:30pm") == ("19:00", "20:30")
    assert parse_time_range("6pm") == ("18:00", None)
    assert parse_time_range("6pjm") == ("18:00", None)


def test_tricity_vibe_city_parsing() -> None:
    assert parse_city("Richland, WA") == "Richland"
    assert parse_city("Irrigon, OR") == "Irrigon"


def test_tricity_vibe_normalized_fixture_shape() -> None:
    events = json.loads(NORMALIZED_PATH.read_text(encoding="utf-8"))

    assert len(events) == 4
    assert {event["source"] for event in events} == {"TriCityVibe"}
    assert all(event["title"] for event in events)
    assert all(event["venue"] for event in events)
    assert all(event["city"] for event in events)
    assert all(event["start_date"] for event in events)
    assert all(event["url"] for event in events)
