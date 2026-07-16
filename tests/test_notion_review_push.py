import json

import httpx

from src.notion_review_push import push_presentation_review
from src.presentation_review import PresentationReviewItem


def _item(kind: str, name: str) -> PresentationReviewItem:
    return PresentationReviewItem(
        kind=kind,
        detected_name=name,
        reason=f"unresolved_{kind.casefold()}",
        source="TestSource",
        event_title="Test Event",
        event_url="https://example.com/event",
        venue="Test Venue",
        city="Richland",
    )


def test_creates_flagged_host_review_record() -> None:
    created = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/query"):
            return httpx.Response(200, json={"results": []})
        created.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"id": "new-page"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = push_presentation_review([_item("HOST", "The Band")], "token", client=client)

    assert result == {"created": 1, "skipped_existing": 0, "skipped_unsupported": 0}
    properties = created[0]["properties"]
    assert properties["Host Name"]["title"][0]["text"]["content"] == "The Band"
    assert properties["Needs Review"]["checkbox"] is True
    assert properties["Review Source URL"]["url"] == "https://example.com/event"


def test_skips_existing_canonical_record() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"results": [{"id": "existing"}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = push_presentation_review([_item("VENUE", "Known Venue")], "token", client=client)

    assert result == {"created": 0, "skipped_existing": 1, "skipped_unsupported": 0}
    assert len(requests) == 1


def test_deduplicates_repeated_review_items_within_push() -> None:
    created = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal created
        if request.url.path.endswith("/query"):
            return httpx.Response(200, json={"results": []})
        created += 1
        return httpx.Response(200, json={"id": "new-page"})

    item = _item("HOST", "Repeated Host")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = push_presentation_review([item, item], "token", client=client)

    assert created == 1
    assert result == {"created": 1, "skipped_existing": 1, "skipped_unsupported": 0}
