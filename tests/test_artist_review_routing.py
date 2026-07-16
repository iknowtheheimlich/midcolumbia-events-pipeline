import json

import httpx

from src.notion_review_push import DEFAULT_ARTISTS_DATA_SOURCE_ID, push_presentation_review
from src.presentation_review import PresentationReviewItem, build_presentation_review


def test_builds_artist_review_item() -> None:
    items = build_presentation_review(
        [
            {
                "title": "Live Music",
                "source": "Test",
                "url": "https://example.com/event",
                "venue": "Test Venue",
                "venue_registry_name": "Test Venue",
                "detected_artist": "The Band",
                "presentation_review_reasons": ["unresolved_artist"],
            }
        ]
    )

    assert len(items) == 1
    assert items[0].kind == "ARTIST"
    assert items[0].detected_name == "The Band"


def test_pushes_artist_to_artist_database() -> None:
    requested_paths = []
    created_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/query"):
            assert DEFAULT_ARTISTS_DATA_SOURCE_ID in request.url.path
            return httpx.Response(200, json={"results": []})
        created_payload.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"id": "artist-page"})

    item = PresentationReviewItem(
        kind="ARTIST",
        detected_name="The Band",
        reason="unresolved_artist",
        source="Test",
        event_title="Live Music",
        event_url="https://example.com/event",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = push_presentation_review([item], "token", client=client)

    assert result["created"] == 1
    assert created_payload["properties"]["Artist Name"]["title"][0]["text"]["content"] == "The Band"
