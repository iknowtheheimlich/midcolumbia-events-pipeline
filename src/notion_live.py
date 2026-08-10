"""Read curated weekly-event rows from the Notion public API."""

from __future__ import annotations

import re
from typing import Any

import httpx

NOTION_API_VERSION = "2026-03-11"
DEFAULT_WEEKLY_DATA_SOURCE_ID = "22138f31-1eb0-8026-a8c7-000bbecdf680"
_STATE_POSTAL_RE = re.compile(
    r"^(?:[A-Z]{2}|Washington|Oregon|Idaho)(?:\s+\d{5}(?:-\d{4})?)?$",
    re.IGNORECASE,
)


def fetch_live_weekly_rows(
    token: str,
    *,
    data_source_id: str = DEFAULT_WEEKLY_DATA_SOURCE_ID,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Query enabled weekly rows and enrich their related Ultimate Venue page."""
    owned_client = client is None
    active = client or httpx.Client(timeout=30.0)
    try:
        pages = _query_pages(active, token, data_source_id)
        venue_cache: dict[str, dict[str, str]] = {}
        rows: list[dict[str, Any]] = []
        for page in pages:
            row = _page_to_row(page)
            relation_ids = _relation_ids(page, "🌆 Ultimate Venues")
            if relation_ids:
                venue_id = relation_ids[0]
                venue = venue_cache.get(venue_id)
                if venue is None:
                    venue = _fetch_venue(active, token, venue_id)
                    venue_cache[venue_id] = venue
                row.update(venue)
            rows.append(row)
        return rows
    finally:
        if owned_client:
            active.close()


def _query_pages(client: httpx.Client, token: str, data_source_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload: dict[str, Any] = {
            "page_size": 100,
            "filter": {
                "and": [
                    {"property": "Weekly", "checkbox": {"equals": True}},
                    {"property": "Generate This Week", "checkbox": {"equals": True}},
                ]
            },
        }
        if cursor:
            payload["start_cursor"] = cursor
        response = client.post(
            f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
            headers=_headers(token),
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
        results.extend(item for item in body.get("results", []) if isinstance(item, dict))
        cursor = body.get("next_cursor")
        if not body.get("has_more") or not cursor:
            return results


def _fetch_venue(client: httpx.Client, token: str, page_id: str) -> dict[str, str]:
    response = client.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(token),
    )
    response.raise_for_status()
    page = response.json()
    props = page.get("properties", {})
    combo = _property_text(props.get("Venue Reddit Combo"))
    venue = _property_text(props.get("Venue Name")) or _property_text(props.get("Official Name"))
    website = _property_text(props.get("Venue Website"))
    address = _property_text(props.get("Address"))
    city = _city_from_address(address)
    return {
        "Venue Reddit Combo": combo,
        "Venue Name": venue,
        "Venue URL": website,
        "City": city,
    }


def _page_to_row(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})
    return {
        "Event Name": _property_text(props.get("Event Name")),
        "Weekly": _property_value(props.get("Weekly")),
        "Generate This Week": _property_value(props.get("Generate This Week")),
        "Days of the Week": _property_text(props.get("Days of the Week")),
        "Date": _property_value(props.get("Date")),
        "Time, Price, Notes": _property_text(props.get("Time, Price, Notes")),
        "Notes Recurring": _property_text(props.get("Notes Recurring")),
    }


def _relation_ids(page: dict[str, Any], name: str) -> list[str]:
    prop = page.get("properties", {}).get(name, {})
    return [item.get("id", "") for item in prop.get("relation", []) if item.get("id")]


def _property_value(prop: Any) -> Any:
    if not isinstance(prop, dict):
        return None
    kind = prop.get("type")
    if kind == "checkbox":
        return prop.get("checkbox")
    if kind == "date":
        value = prop.get("date") or {}
        return value.get("start")
    return _property_text(prop)


def _property_text(prop: Any) -> str:
    if not isinstance(prop, dict):
        return ""
    kind = prop.get("type")
    value = prop.get(kind) if kind else None
    if kind in {"title", "rich_text"}:
        return "".join(item.get("plain_text", "") for item in value or [])
    if kind == "url":
        return value or ""
    if kind == "formula":
        return _formula_text(value)
    if kind == "rollup":
        return _rollup_text(value)
    if kind == "select":
        return (value or {}).get("name", "")
    return "" if value is None else str(value)


def _formula_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    kind = value.get("type")
    result = value.get(kind) if kind else None
    return "" if result is None else str(result)


def _rollup_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    kind = value.get("type")
    if kind == "array":
        return "".join(_property_text(item) for item in value.get("array", []))
    result = value.get(kind) if kind else None
    return "" if result is None else str(result)


def _city_from_address(address: str) -> str:
    parts = [part.strip() for part in address.split(",") if part.strip()]
    if parts and parts[-1].casefold() in {"usa", "united states"}:
        parts.pop()
    if len(parts) >= 2 and _STATE_POSTAL_RE.fullmatch(parts[-1]):
        return parts[-2]
    return parts[-3] if len(parts) >= 3 else ""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
