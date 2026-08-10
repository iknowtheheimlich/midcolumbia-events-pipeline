import json

import httpx

from src.notion_live import _city_from_address, fetch_live_weekly_rows


def _rich_text(value: str) -> dict:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def _title(value: str) -> dict:
    return {"type": "title", "title": [{"plain_text": value}]}


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
