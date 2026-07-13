import json
from pathlib import Path

import pytest

from adapters.allevents.parser import parse_pages
from adapters.harvest import get_harvester, normalize_allevents


def json_ld_page(*nodes: dict) -> str:
    payload = {"@context": "https://schema.org", "@graph": list(nodes)}
    return (
        '<html><head><script type="application/ld+json">'
        + json.dumps(payload)
        + "</script></head><body>recommendation prose ignored</body></html>"
    )


def event_node(**overrides):
    event = {
        "@type": "MusicEvent",
        "name": "Summer Concert",
        "description": "Live music by the river.",
        "startDate": "2026-07-18T19:00:00-07:00",
        "endDate": "2026-07-18T21:00:00-07:00",
        "url": "https://allevents.in/kennewick/summer-concert/2400028835606846",
        "location": {
            "@type": "Place",
            "name": "Columbia Park",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "6007 Columbia Park Trail",
                "addressLocality": "Kennewick",
                "addressRegion": "WA",
                "postalCode": "99336",
            },
        },
        "organizer": {"@type": "Organization", "name": "River Events"},
        "image": ["https://example.org/event.jpg"],
        "keywords": ["Music", "Community"],
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
    }
    event.update(overrides)
    return event


def test_parser_normalizes_json_ld_event() -> None:
    events = parse_pages({"Kennewick": json_ld_page(event_node())})

    assert events == [
        {
            "title": "Summer Concert",
            "description": "Live music by the river.",
            "venue": "Columbia Park",
            "city": "Kennewick",
            "state": "WA",
            "address": "6007 Columbia Park Trail, Kennewick, WA, 99336",
            "start_date": "2026-07-18",
            "start_time": "19:00",
            "end_date": "2026-07-18",
            "end_time": "21:00",
            "organization": "River Events",
            "url": "https://allevents.in/kennewick/summer-concert/2400028835606846",
            "external_url": "https://allevents.in/kennewick/summer-concert/2400028835606846",
            "source": "AllEvents",
            "source_event_id": "2400028835606846",
            "source_category": "Music, Community",
            "image_url": "https://example.org/event.jpg",
            "event_status": "EventScheduled",
            "attendance_mode": "OfflineEventAttendanceMode",
        }
    ]


def test_parser_deduplicates_same_listing_across_city_pages() -> None:
    page = json_ld_page(event_node())
    events = parse_pages({"Kennewick": page, "Richland": page})

    assert len(events) == 1


def test_parser_ignores_non_event_json_ld_and_incomplete_events() -> None:
    page = json_ld_page(
        {"@type": "WebSite", "name": "AllEvents"},
        event_node(name=""),
        event_node(url=""),
    )

    assert parse_pages({"Kennewick": page}) == []


def test_saved_city_page_handles_itemlists_entities_and_organizer_lists() -> None:
    html = Path("fixtures/allevents/saved_city_page.html").read_text(encoding="utf-8")

    events = parse_pages({"Kennewick": html})

    assert len(events) == 2
    water_follies = events[0]
    assert water_follies["title"] == (
        "2026 Tri-City Water Follies Apollo Columbia Cup & STCU Over-the-River Air Show"
    )
    assert water_follies["organization"] == "Water Follies, STCU"
    assert water_follies["start_date"] == "2026-07-24"
    assert water_follies["end_date"] == "2026-07-26"
    assert "start_time" not in water_follies
    assert "end_time" not in water_follies


def test_saved_city_page_preserves_explicit_times_and_list_location() -> None:
    html = Path("fixtures/allevents/saved_city_page.html").read_text(encoding="utf-8")

    events = parse_pages({"Kennewick": html})
    evening = next(event for event in events if event["title"] == "Evening Concert")

    assert evening["start_time"] == "19:00"
    assert evening["end_time"] == "21:00"
    assert evening["venue"] == "Columbia Park"
    assert evening["organization"] == "River Events"


def test_normalizer_requires_city_html_mapping() -> None:
    with pytest.raises(TypeError, match="mapping of city names to HTML"):
        normalize_allevents("<html></html>")


def test_harvester_is_registered() -> None:
    harvester = get_harvester("AllEvents")

    assert harvester.source_name == "AllEvents"
