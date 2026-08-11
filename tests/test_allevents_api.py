from datetime import date
from email.message import Message
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from adapters.allevents.api import (
    CITY_QUERIES,
    _decode_api_response,
    _request_payload,
    harvest_allevents_api,
    normalize_api_event,
    normalize_api_responses,
)
from adapters.registry import get_adapter
from src.harvest_health import assess_harvest_health


class _Response:
    def __init__(self, body: bytes, *, status: int = 200, content_type: str) -> None:
        self.status = status
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self) -> bytes:
        return self._body


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


def test_rejects_observed_html_session_response_with_diagnostic_context():
    response = _Response(
        ("Not available at this moment" + "x" * 200).encode("utf-8"),
        content_type="text/html; charset=UTF-8",
    )

    with pytest.raises(RuntimeError) as captured:
        _decode_api_response(response)

    diagnostic = str(captured.value)
    assert "AllEvents session/API rejection" in diagnostic
    assert "HTTP 200" in diagnostic
    assert "Content-Type 'text/html'" in diagnostic
    assert "Not available at this moment" in diagnostic
    assert len(diagnostic.split("response prefix: ", 1)[1].strip("'")) <= 160


def test_accepts_valid_json_response_without_changing_payload():
    payload = {"error": 0, "page": 1, "search_result": []}
    response = _Response(
        json.dumps(payload).encode("utf-8"),
        content_type="application/json; charset=utf-8",
    )

    assert _decode_api_response(response) == payload


def test_rejected_city_is_attributed_and_successful_city_results_remain_usable(monkeypatch):
    target = date(2026, 7, 19)

    def fetch_json(_url, *, body, headers):
        del headers
        payload = json.loads(body)
        if payload["city"] == "Pasco":
            raise RuntimeError(
                "AllEvents session/API rejection: HTTP 200; Content-Type 'text/html'; "
                "response prefix: 'Not available at this moment'"
            )
        return {"error": 0, "search_result": [_row(event_id=payload["city"])]}

    monkeypatch.setattr("adapters.allevents.api.save_raw_fixture", lambda *_args: None)
    monkeypatch.setattr("adapters.allevents.api.generated_raw_path", lambda _adapter: Path("raw.json"))
    adapter = get_adapter("AllEvents")
    result = harvest_allevents_api(adapter, week_start=target, days=1, fetch_json=fetch_json)
    health = assess_harvest_health([adapter], [result])

    assert result.normalized_events
    assert "2026-07-19|Pasco: RuntimeError: AllEvents session/API rejection" in result.error
    assert health.sources[0].status == "PARTIAL"
    assert health.sources[0].reason == result.error


def test_dns_failure_remains_distinct_from_session_rejection(monkeypatch):
    def fetch_json(_url, *, body, headers):
        del headers
        payload = json.loads(body)
        if payload["city"] == "Pasco":
            raise URLError("[Errno 11001] getaddrinfo failed")
        return {"error": 0, "search_result": [_row(event_id=payload["city"])]}

    monkeypatch.setattr("adapters.allevents.api.save_raw_fixture", lambda *_args: None)
    monkeypatch.setattr("adapters.allevents.api.generated_raw_path", lambda _adapter: Path("raw.json"))
    result = harvest_allevents_api(
        get_adapter("AllEvents"),
        week_start=date(2026, 7, 19),
        days=1,
        fetch_json=fetch_json,
    )

    assert "2026-07-19|Pasco: URLError: <urlopen error [Errno 11001] getaddrinfo failed>" in result.error
    assert "session/API rejection" not in result.error


def _connection_reset() -> URLError:
    return URLError(ConnectionResetError(10054, "An existing connection was forcibly closed by the remote host"))


def test_city_connection_reset_recovers_after_exactly_one_retry(monkeypatch, caplog):
    calls: dict[tuple[str, str], int] = {}

    def fetch_json(_url, *, body, headers):
        del headers
        payload = json.loads(body)
        key = (payload["start_date"].split()[0], payload["city"])
        calls[key] = calls.get(key, 0) + 1
        if key == ("2026-08-11", "Kennewick") and calls[key] == 1:
            raise _connection_reset()
        return {"error": 0, "search_result": [_row(event_id=payload["city"])]}

    monkeypatch.setattr("adapters.allevents.api.time.sleep", lambda seconds: None)
    monkeypatch.setattr("adapters.allevents.api.save_raw_fixture", lambda *_args: None)
    monkeypatch.setattr("adapters.allevents.api.generated_raw_path", lambda _adapter: Path("raw.json"))
    result = harvest_allevents_api(
        get_adapter("AllEvents"),
        week_start=date(2026, 8, 11),
        days=1,
        fetch_json=fetch_json,
    )

    assert result.error is None
    assert calls[("2026-08-11", "Kennewick")] == 2
    assert all(count == 1 for key, count in calls.items() if key != ("2026-08-11", "Kennewick"))
    assert "allevents_city_request_connection_reset_recovered" in caplog.text
    assert "context=2026-08-11|Kennewick" in caplog.text


def test_two_city_connection_resets_retain_partial_results_and_diagnostics(monkeypatch, caplog):
    calls: dict[str, int] = {}

    def fetch_json(_url, *, body, headers):
        del headers
        payload = json.loads(body)
        city = payload["city"]
        calls[city] = calls.get(city, 0) + 1
        if city == "Kennewick":
            raise _connection_reset()
        return {"error": 0, "search_result": [_row(event_id=city)]}

    monkeypatch.setattr("adapters.allevents.api.time.sleep", lambda seconds: None)
    monkeypatch.setattr("adapters.allevents.api.save_raw_fixture", lambda *_args: None)
    monkeypatch.setattr("adapters.allevents.api.generated_raw_path", lambda _adapter: Path("raw.json"))
    adapter = get_adapter("AllEvents")
    result = harvest_allevents_api(
        adapter,
        week_start=date(2026, 8, 11),
        days=1,
        fetch_json=fetch_json,
    )
    health = assess_harvest_health([adapter], [result])

    assert calls["Kennewick"] == 2
    assert result.normalized_events
    assert "2026-08-11|Kennewick: URLError" in result.error
    assert health.sources[0].status == "PARTIAL"
    assert "allevents_city_request_connection_reset_retry_failed" in caplog.text
    assert "context=2026-08-11|Kennewick" in caplog.text


@pytest.mark.parametrize(
    "failure",
    (
        URLError("[Errno 11001] getaddrinfo failed"),
        URLError(ConnectionRefusedError(10061, "No connection could be made")),
        HTTPError("https://allevents.in/api", 503, "Service Unavailable", {}, None),
    ),
)
def test_unrelated_url_errors_are_not_retried(monkeypatch, failure):
    calls = 0

    def fetch_json(_url, *, body, headers):
        nonlocal calls
        del headers
        payload = json.loads(body)
        if payload["city"] == "Kennewick":
            calls += 1
            raise failure
        return {"error": 0, "search_result": [_row(event_id=payload["city"])]}

    def unexpected_sleep(_seconds):
        raise AssertionError("unrelated URLError must not sleep or retry")

    monkeypatch.setattr("adapters.allevents.api.time.sleep", unexpected_sleep)
    monkeypatch.setattr("adapters.allevents.api.save_raw_fixture", lambda *_args: None)
    monkeypatch.setattr("adapters.allevents.api.generated_raw_path", lambda _adapter: Path("raw.json"))
    result = harvest_allevents_api(
        get_adapter("AllEvents"),
        week_start=date(2026, 8, 11),
        days=1,
        fetch_json=fetch_json,
    )

    assert calls == 1
    assert result.error is not None


def test_session_rejection_is_not_retried(monkeypatch):
    calls = 0

    def fetch_json(_url, *, body, headers):
        nonlocal calls
        del headers
        payload = json.loads(body)
        if payload["city"] == "Kennewick":
            calls += 1
            raise RuntimeError("AllEvents session/API rejection")
        return {"error": 0, "search_result": [_row(event_id=payload["city"])]}

    monkeypatch.setattr(
        "adapters.allevents.api.time.sleep",
        lambda _seconds: (_ for _ in ()).throw(AssertionError("session rejection retried")),
    )
    monkeypatch.setattr("adapters.allevents.api.save_raw_fixture", lambda *_args: None)
    monkeypatch.setattr("adapters.allevents.api.generated_raw_path", lambda _adapter: Path("raw.json"))
    result = harvest_allevents_api(
        get_adapter("AllEvents"),
        week_start=date(2026, 8, 11),
        days=1,
        fetch_json=fetch_json,
    )

    assert calls == 1
    assert "AllEvents session/API rejection" in result.error


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


def test_description_range_overrides_conflicting_epoch():
    event = normalize_api_event(
        _row(
            event_id="200030322410755",
            eventname="OFFICIAL FIFA WATCH PARTY",
            start_time="1784462400",
            end_time="1784491200",
            description="Sunday, July 19. 12:00 PM – 8:00 PM. Free family event.",
        )
    )
    assert event is not None
    assert event["start_time"] == "12:00"
    assert event["end_time"] == "20:00"
    assert event["source_time_reason"] == "description_explicit_time_range"


@pytest.mark.parametrize(
    "description",
    [
        "A Quiet Life performs Friday. 9 PM - Close.",
        "People Our Age Suck takes the stage at 9 PM – Close.",
    ],
)
def test_explicit_open_ended_description_time_overrides_conflicting_epoch(description: str):
    event = normalize_api_event(
        _row(
            event_id="200030492623509",
            start_time="1786750800",
            end_time="1786754400",
            description=description,
        )
    )

    assert event is not None
    assert event["start_time"] == "21:00"
    assert event.get("end_time") is None
    assert event["source_time_reason"] == "description_explicit_open_ended_start"


def test_vague_description_does_not_override_api_epoch():
    event = normalize_api_event(
        _row(description="Live music throughout the evening.")
    )

    assert event is not None
    assert event["start_time"] == "11:00"
    assert event["source_time_reason"] == "utc_epoch_converted"


def test_description_start_and_end_cues_override_conflicting_epoch():
    event = normalize_api_event(
        _row(
            event_id="200030343620926",
            eventname="IHB Brews & Tattoos with the Mad Tatter",
            start_time="1784210400",
            end_time="1784232000",
            description=(
                "The Mad Tatter will start taking clients at 2pm sharp. "
                "Don't miss out; event ends at 8pm."
            ),
        )
    )
    assert event is not None
    assert event["start_time"] == "14:00"
    assert event["end_time"] == "20:00"
    assert event["source_time_reason"] == "description_explicit_time_range"


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
