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
        "timezone": "-07:00",
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


def test_normalizes_true_utc_epoch_to_local_time():
    event = normalize_api_event(_row())
    assert event is not None
    assert event["start_date"] == "2026-07-13"
    assert event["start_time"] == "11:00"
    assert event["end_time"] == "12:00"
    assert event["source_time_reason"] == "utc_epoch_converted"
    assert event["venue"] == "The Pacific Campus"
    assert event["city"] == "Kennewick"


def test_repairs_market_wall_clock_epoch_instead_of_rendering_3am():
    event = normalize_api_event(
        _row(
            event_id="200030137583036",
            eventname="Mobile Market - Kennewick",
            start_time="1784023200",
            end_time="1784030400",
            description="Free food drive-thru market for families.",
        )
    )
    assert event is not None
    assert event["start_time"] == "10:00"
    assert event["end_time"] == "12:00"
    assert event["source_time_reason"] == "wall_clock_epoch_repaired"


def test_repairs_title_embedded_daytime_wall_clock_epoch():
    event = normalize_api_event(
        _row(
            event_id="200030302941915",
            eventname="Island Santa at Wheat Head 11-2 | Open 11-9",
            start_time="1784372400",
            end_time="1784372400",
            description="Christmas in July with Island Santa photos 11-2.",
        )
    )
    assert event is not None
    assert event["start_time"] == "11:00"
    assert event["end_time"] == "11:00"
    assert event["source_time_reason"] == "wall_clock_epoch_repaired"


def test_repairs_daytime_race_wall_clock_epoch():
    event = normalize_api_event(
        _row(
            event_id="200029787547806",
            eventname="Christmas 5K/10K/Half Marathon in July - Richland",
            start_time="1784448000",
            end_time="1784448000",
        )
    )
    assert event is not None
    assert event["start_time"] == "08:00"
    assert event["source_time_reason"] == "wall_clock_epoch_repaired"


def test_preserves_explicit_overnight_event_at_1am():
    event = normalize_api_event(
        _row(
            eventname="Midnight After Party",
            start_time="1784448000",
            end_time="1784451600",
            description="Late-night overnight event.",
        )
    )
    assert event is not None
    assert event["start_time"] == "01:00"
    assert event["source_time_reason"] == "utc_epoch_converted"


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
