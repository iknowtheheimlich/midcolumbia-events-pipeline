"""Push unresolved presentation metadata into curated Notion review queues.

This module never updates existing canonical records. It creates clearly flagged review
records only when the detected name is not already present in the target data source.
"""

from __future__ import annotations

from typing import Any, Iterable

import httpx

from src.presentation_review import PresentationReviewItem

NOTION_API_VERSION = "2026-03-11"
DEFAULT_VENUES_DATA_SOURCE_ID = "36238f31-1eb0-8033-bd62-000ba0ba9470"
DEFAULT_HOSTS_DATA_SOURCE_ID = "34e38f31-1eb0-8008-90fa-000bac2c29a4"
DEFAULT_ARTISTS_DATA_SOURCE_ID = "173808c6-7d5b-4597-80b9-364984324fe5"


def push_presentation_review(
    items: Iterable[PresentationReviewItem],
    token: str,
    *,
    venues_data_source_id: str = DEFAULT_VENUES_DATA_SOURCE_ID,
    hosts_data_source_id: str = DEFAULT_HOSTS_DATA_SOURCE_ID,
    artists_data_source_id: str = DEFAULT_ARTISTS_DATA_SOURCE_ID,
    client: httpx.Client | None = None,
) -> dict[str, int]:
    """Create missing review records and return created/skipped counts."""
    owned_client = client is None
    active = client or httpx.Client(timeout=30.0)
    counts = {"created": 0, "skipped_existing": 0, "skipped_unsupported": 0}
    try:
        existing_cache: dict[tuple[str, str], bool] = {}
        for item in items:
            if item.kind == "VENUE":
                data_source_id = venues_data_source_id
                title_property = "Venue Name"
            elif item.kind == "HOST":
                data_source_id = hosts_data_source_id
                title_property = "Host Name"
            elif item.kind == "ARTIST":
                data_source_id = artists_data_source_id
                title_property = "Artist Name"
            else:
                counts["skipped_unsupported"] += 1
                continue

            cache_key = (data_source_id, item.detected_name.casefold())
            exists = existing_cache.get(cache_key)
            if exists is None:
                exists = _record_exists(
                    active,
                    token,
                    data_source_id,
                    title_property,
                    item.detected_name,
                )
                existing_cache[cache_key] = exists
            if exists:
                counts["skipped_existing"] += 1
                continue

            _create_review_record(
                active,
                token,
                data_source_id,
                title_property,
                item,
            )
            existing_cache[cache_key] = True
            counts["created"] += 1
        return counts
    finally:
        if owned_client:
            active.close()


def _record_exists(
    client: httpx.Client,
    token: str,
    data_source_id: str,
    title_property: str,
    detected_name: str,
) -> bool:
    response = client.post(
        f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
        headers=_headers(token),
        json={
            "page_size": 1,
            "filter": {
                "property": title_property,
                "title": {"equals": detected_name},
            },
        },
    )
    response.raise_for_status()
    return bool(response.json().get("results"))


def _create_review_record(
    client: httpx.Client,
    token: str,
    data_source_id: str,
    title_property: str,
    item: PresentationReviewItem,
) -> None:
    notes = f"{item.reason}; source={item.source}; event={item.event_title}"
    if item.city:
        notes += f"; city={item.city}"
    payload: dict[str, Any] = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": {
            title_property: {
                "type": "title",
                "title": [{"type": "text", "text": {"content": item.detected_name}}],
            },
            "Needs Review": {"type": "checkbox", "checkbox": True},
            "Review Notes": {
                "type": "rich_text",
                "rich_text": [{"type": "text", "text": {"content": notes[:2000]}}],
            },
        },
    }
    if item.event_url:
        payload["properties"]["Review Source URL"] = {
            "type": "url",
            "url": item.event_url,
        }
    response = client.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(token),
        json=payload,
    )
    response.raise_for_status()


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
