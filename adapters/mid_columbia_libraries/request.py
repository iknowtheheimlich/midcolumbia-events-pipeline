"""Mid-Columbia Libraries request helpers."""

from __future__ import annotations

from urllib.parse import urlencode

from adapters.mid_columbia_libraries.config import EVENTS_URL


def build_events_url(*, page: int | None = None, location: str | None = None) -> str:
    """Build a stable Mid-Columbia Libraries events listing URL."""
    params: dict[str, str] = {}
    if page is not None and page > 0:
        params["page"] = str(page)
    if location:
        params["location"] = location

    query = urlencode(params)
    return f"{EVENTS_URL}?{query}" if query else EVENTS_URL
