from __future__ import annotations

from adapters.mcl.parser import Link, parse_meta, parse_time_range, parse_tokens


def test_mcl_parser_normalizes_listing_tokens() -> None:
    tokens = [
        "Jul 5 Sun",
        Link("Coffee and Conversation", "/events/coffee-and-conversation"),
        "1:00 - 3:00pm",
        "Device help and reading recommendations.",
        "Pasco Adult Program Adults",
        "Jul 6 Mon",
        Link("Baby Storytime", "/events/baby-storytime"),
        "10:30 - 11:30am",
        "Stories, songs, and early literacy play.",
        "West Richland Storytime 0-5",
    ]

    events = parse_tokens(tokens, year=2026)

    assert len(events) == 2
    assert events[0]["source"] == "MidColumbiaLibraries"
    assert events[0]["start_date"] == "2026-07-05"
    assert events[0]["start_time"] == "13:00"
    assert events[0]["end_time"] == "15:00"
    assert events[0]["venue"] == "Mid-Columbia Library (Pasco)"
    assert events[1]["city"] == "West Richland"
    assert events[1]["category"] == "Storytime"


def test_mcl_parser_time_and_meta_helpers() -> None:
    assert parse_time_range("10:30 - 11:30am") == ("10:30", "11:30")
    assert parse_time_range("4:00 - 5:00pm") == ("16:00", "17:00")
    assert parse_time_range("10:00am") == ("10:00", None)

    assert parse_meta("West Richland Storytime 0-5") == (
        "West Richland",
        "Storytime",
        "0-5",
    )