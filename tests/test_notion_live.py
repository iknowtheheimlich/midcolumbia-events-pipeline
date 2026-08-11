import json
import logging
import socket

import httpx
import pytest

import src.notion_live as notion_live
from src.notion_live import _city_from_address, fetch_live_weekly_rows


def _rich_text(value: str) -> dict:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def _title(value: str) -> dict:
    return {"type": "title", "title": [{"plain_text": value}]}


def _resolver_connect_error() -> httpx.ConnectError:
    try:
        raise socket.gaierror(11001, "getaddrinfo failed")
    except socket.gaierror as cause:
        error = httpx.ConnectError("[Errno 11001] getaddrinfo failed")
        error.__cause__ = cause
        return error


def _connection_reset_read_error() -> httpx.ReadError:
    try:
        raise ConnectionResetError(
            10054,
            "An existing connection was forcibly closed by the remote host",
        )
    except ConnectionResetError as cause:
        error = httpx.ReadError(
            "[WinError 10054] An existing connection was forcibly closed by the remote host"
        )
        error.__cause__ = cause
        return error


def test_city_from_address_supports_state_zip_without_country() -> None:
    assert _city_from_address("530 Columbia Point Drive, Richland, WA 99352") == "Richland"


def test_city_from_address_supports_trailing_country() -> None:
    assert _city_from_address("3300 W Clearwater Ave, Kennewick, WA 99336, USA") == "Kennewick"


def test_fetches_enabled_weekly_rows_and_enriches_venue() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/query"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "properties": {
                                "Event Name": _title("Trivia Night"),
                                "Weekly": {"type": "checkbox", "checkbox": True},
                                "Generate This Week": {"type": "checkbox", "checkbox": True},
                                "Days of the Week": _rich_text("Wednesday"),
                                "Date": {"type": "date", "date": None},
                                "Time, Price, Notes": _rich_text("6:30-8:30p"),
                                "Notes Recurring": _rich_text("Weekly"),
                                "🌆 Ultimate Venues": {
                                    "type": "relation",
                                    "relation": [{"id": "venue-1"}],
                                },
                            }
                        }
                    ],
                    "has_more": False,
                    "next_cursor": None,
                },
            )
        return httpx.Response(
            200,
            json={
                "properties": {
                    "Venue Name": _title("Solar Spirits"),
                    "Venue Website": {"type": "url", "url": "https://solar.example/"},
                    "Address": _rich_text("123 Main St, Richland, WA, USA"),
                    "Venue Reddit Combo": {
                        "type": "formula",
                        "formula": {
                            "type": "string",
                            "string": "[Solar Spirits](https://solar.example/), Richland",
                        },
                    },
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows = fetch_live_weekly_rows("token", client=client)

    assert rows == [
        {
            "Event Name": "Trivia Night",
            "Weekly": True,
            "Generate This Week": True,
            "Days of the Week": "Wednesday",
            "Date": None,
            "Time, Price, Notes": "6:30-8:30p",
            "Notes Recurring": "Weekly",
            "Venue Reddit Combo": "[Solar Spirits](https://solar.example/), Richland",
            "Venue Name": "Solar Spirits",
            "Venue URL": "https://solar.example/",
            "City": "Richland",
        }
    ]


def test_reuses_related_venue_request_for_multiple_rows() -> None:
    venue_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal venue_requests
        if request.url.path.endswith("/query"):
            page = {
                "properties": {
                    "Event Name": _title("Event"),
                    "Weekly": {"type": "checkbox", "checkbox": True},
                    "Generate This Week": {"type": "checkbox", "checkbox": True},
                    "🌆 Ultimate Venues": {"type": "relation", "relation": [{"id": "venue-1"}]},
                }
            }
            return httpx.Response(200, json={"results": [page, page], "has_more": False})
        venue_requests += 1
        return httpx.Response(200, json={"properties": {"Venue Name": _title("Venue")}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetch_live_weekly_rows("token", client=client)

    assert venue_requests == 1


def test_sends_weekly_and_generate_filters() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"results": [], "has_more": False})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetch_live_weekly_rows("token", client=client)

    assert captured["filter"] == {
        "and": [
            {"property": "Weekly", "checkbox": {"equals": True}},
            {"property": "Generate This Week", "checkbox": {"equals": True}},
        ]
    }


def test_initial_resolver_failure_retries_once_and_recovers(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    requests = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            raise _resolver_connect_error()
        return httpx.Response(200, json={"results": [], "has_more": False})

    monkeypatch.setattr(notion_live.time, "sleep", sleeps.append)
    caplog.set_level(logging.WARNING, logger="src.notion_live")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert fetch_live_weekly_rows("token", client=client) == []

    assert requests == 2
    assert sleeps == [1.0]
    assert "initial_notion_query_resolver_failure" in caplog.text
    assert "timestamp=" in caplog.text
    assert "initial_notion_query_resolver_recovered" in caplog.text
    first_record = next(
        record for record in caplog.records
        if record.message.startswith("initial_notion_query_resolver_failure")
    )
    assert isinstance(first_record.exc_info[1], httpx.ConnectError)


def test_two_initial_resolver_failures_abort_with_both_errors_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors = [_resolver_connect_error(), _resolver_connect_error()]
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        error = errors[requests]
        requests += 1
        raise error

    monkeypatch.setattr(notion_live.time, "sleep", lambda _: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ConnectError) as caught:
            fetch_live_weekly_rows("token", client=client)

    assert requests == 2
    assert caught.value is errors[1]
    assert any("first_error=ConnectError" in note for note in caught.value.__notes__)
    assert any("first_attempt_timestamp=" in note for note in caught.value.__notes__)


@pytest.mark.parametrize("status_code", [400, 401, 500])
def test_http_errors_are_not_retried(status_code: int) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(status_code, json={"message": "no"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            fetch_live_weekly_rows("token", client=client)

    assert requests == 1


def test_unrelated_connect_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = 0
    slept = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        raise httpx.ConnectError("connection refused")

    def unexpected_sleep(_: float) -> None:
        nonlocal slept
        slept = True

    monkeypatch.setattr(notion_live.time, "sleep", unexpected_sleep)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ConnectError, match="connection refused"):
            fetch_live_weekly_rows("token", client=client)

    assert requests == 1
    assert slept is False


def test_resolver_failure_during_pagination_is_not_retried() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(
                200,
                json={"results": [], "has_more": True, "next_cursor": "next"},
            )
        raise _resolver_connect_error()

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ConnectError):
            fetch_live_weekly_rows("token", client=client)

    assert requests == 2


def test_venue_connection_reset_retries_exact_request_once_and_recovers(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    venue_requests: list[str] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/query"):
            page = {
                "properties": {
                    "Event Name": _title("Event"),
                    "Weekly": {"type": "checkbox", "checkbox": True},
                    "Generate This Week": {"type": "checkbox", "checkbox": True},
                    "🌆 Ultimate Venues": {
                        "type": "relation",
                        "relation": [{"id": "venue-1"}],
                    },
                }
            }
            return httpx.Response(200, json={"results": [page], "has_more": False})
        venue_requests.append(str(request.url))
        if len(venue_requests) == 1:
            raise _connection_reset_read_error()
        return httpx.Response(200, json={"properties": {"Venue Name": _title("Venue")}})

    monkeypatch.setattr(notion_live.time, "sleep", sleeps.append)
    caplog.set_level(logging.WARNING, logger="src.notion_live")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows = fetch_live_weekly_rows("token", client=client)

    assert rows[0]["Venue Name"] == "Venue"
    assert venue_requests == [
        "https://api.notion.com/v1/pages/venue-1",
        "https://api.notion.com/v1/pages/venue-1",
    ]
    assert sleeps == [1.0]
    assert "notion_venue_fetch_connection_reset timestamp=" in caplog.text
    assert "notion_venue_fetch_connection_reset_recovered" in caplog.text
    first_record = next(
        record for record in caplog.records
        if record.message.startswith("notion_venue_fetch_connection_reset timestamp=")
    )
    assert isinstance(first_record.exc_info[1], httpx.ReadError)


def test_two_venue_connection_resets_abort_with_both_errors_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors = [_connection_reset_read_error(), _connection_reset_read_error()]
    venue_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal venue_requests
        if request.url.path.endswith("/query"):
            page = {
                "properties": {
                    "🌆 Ultimate Venues": {
                        "type": "relation",
                        "relation": [{"id": "venue-1"}],
                    }
                }
            }
            return httpx.Response(200, json={"results": [page], "has_more": False})
        error = errors[venue_requests]
        venue_requests += 1
        raise error

    monkeypatch.setattr(notion_live.time, "sleep", lambda _: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ReadError) as caught:
            fetch_live_weekly_rows("token", client=client)

    assert venue_requests == 2
    assert caught.value is errors[1]
    assert any("first_error=ReadError" in note for note in caught.value.__notes__)
    assert any("first_attempt_timestamp=" in note for note in caught.value.__notes__)


def test_unrelated_venue_read_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    venue_requests = 0
    slept = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal venue_requests
        if request.url.path.endswith("/query"):
            page = {
                "properties": {
                    "🌆 Ultimate Venues": {
                        "type": "relation",
                        "relation": [{"id": "venue-1"}],
                    }
                }
            }
            return httpx.Response(200, json={"results": [page], "has_more": False})
        venue_requests += 1
        raise httpx.ReadError("TLS stream ended unexpectedly")

    def unexpected_sleep(_: float) -> None:
        nonlocal slept
        slept = True

    monkeypatch.setattr(notion_live.time, "sleep", unexpected_sleep)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ReadError, match="TLS stream ended"):
            fetch_live_weekly_rows("token", client=client)

    assert venue_requests == 1
    assert slept is False


def test_venue_http_error_is_not_retried() -> None:
    venue_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal venue_requests
        if request.url.path.endswith("/query"):
            page = {
                "properties": {
                    "🌆 Ultimate Venues": {
                        "type": "relation",
                        "relation": [{"id": "venue-1"}],
                    }
                }
            }
            return httpx.Response(200, json={"results": [page], "has_more": False})
        venue_requests += 1
        return httpx.Response(401, json={"message": "unauthorized"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            fetch_live_weekly_rows("token", client=client)

    assert venue_requests == 1
