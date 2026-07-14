from datetime import date
import json

from adapters.allevents.api import (
    CITY_QUERIES,
    _request_payload,
    normalize_api_event,
    normalize_api_responses,
)


def _row(**overrides):
    row = {
        "event_id": "200030259970605",
        "eventname": "FREE P.A.C. Trial Day",
        "start_time": "1783965600",
        "end_time": "1783969200",
        "description": "Join us for a <b>FREE</b> trial day.",
        "location": "1350 North Grant St., Kennewick, WA",
        "venue": {
            "venue": "The Pacific Campus",
            "street": "1350 N Grant St, Kennewick, WA 99336",
            "city": "Kennewick",
            "state": "WA",
            "latitude": "46.22474",
            "longitude": "-119.19301",
        },
        "event_url": "https://allevents.in/kennewick/event/200030259970605?ref=eventsearch",
        "banner_url": "https://example.org/banner.jpg",
        "ticket": {"has_tickets": False},
        "recurring_event_details": {"has_slots": False},
    }
    row.update(overrides)
    return row


def test_city_queries_do_not_seed_hermiston():
    assert "Hermiston" not in {item["city"] for item in CITY_QUERIES}


def test_request_payload_is_day_scoped():
    payload = _request_payload(date(2026, 7, 13), CITY_QUERIES[0])
    assert payload["start_date"] == "2026-07-13 00:00"
    assert payload["end_date"] == "2026-07-13 23:59"
    assert payload["search_scope"] == "city"


def test_normalizes_api_record_to_local_time():
    event = normalize_api_event(_row())
    assert event is not None
    assert event["start_date"] == "2026-07-13"
    assert event["start_time"] == "11:00"
    assert event["end_time"] == "12:00"
    assert event["venue"] == "The Pacific Campus"
    assert event["city"] == "Kennewick"


def test_cleans_description_and_tracking_query():
    event = normalize_api_event(_row())
    assert event is not None
    assert event["description"] == "Join us for a FREE trial day."
    assert event["url"] == "https://allevents.in/kennewick/event/200030259970605"


def test_rejects_record_without_required_identity():
    assert normalize_api_event(_row(event_id=None)) is None
    assert normalize_api_event(_row(start_time=None)) is None


def test_overlapping_city_results_are_deduplicated():
    response = {"error": 0, "search_result": [_row()]}
    events = normalize_api_responses({"Kennewick": response, "Pasco": response})
    assert len(events) == 1
    assert events[0]["source_event_id"] == "200030259970605"


def test_preserves_structured_ticket_details():
    event = normalize_api_event(
        _row(
            tickets={
                "has_tickets": True,
                "ticket_url": "https://tickets.example.org/buy?campaign=x",
                "price_display": "$15",
            }
        )
    )
    assert event is not None
    assert event["ticket_url"] == "https://tickets.example.org/buy"
    assert event["cost"] == "$15"
