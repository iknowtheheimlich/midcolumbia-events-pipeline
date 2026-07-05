"""Mid-Columbia Libraries request builder."""

from __future__ import annotations

from urllib.parse import urlencode

from adapters.mid_columbia_libraries.config import EVENTS_URL


def build_events_url(page: int = 0) -> str:
    """Build the MCL upcoming events listing URL.

    Drupal pagers are zero-based. Page 0 is the default first page.
    """
    if page <= 0:
        return EVENTS_URL
    return f"{EVENTS_URL}?{urlencode({'page': page})}"
