"""Visit Tri-Cities Algolia request builder."""

from __future__ import annotations

from urllib.parse import urlencode

from adapters.algolia.payload import build_multi_query_payload
from adapters.visit_tricities.config import ALGOLIA_EVENT_FILTERS, ALGOLIA_INDEX_NAME

DEFAULT_HITS_PER_PAGE = 24


def build_visit_tricities_params(page: int = 0, hits_per_page: int = DEFAULT_HITS_PER_PAGE) -> str:
    """Build the URL-encoded Algolia params string captured from VTC.

    The original site request uses a newline-separated rendering in DevTools,
    but Algolia expects an application/x-www-form-urlencoded params string.
    """
    if page < 0:
        raise ValueError("page must be >= 0")
    if hits_per_page <= 0:
        raise ValueError("hits_per_page must be > 0")

    params = {
        "clickAnalytics": "true",
        "facets": '["*"]',
        "filters": ALGOLIA_EVENT_FILTERS,
        "highlightPostTag": "__/ais-highlight__",
        "highlightPreTag": "__ais-highlight__",
        "hitsPerPage": str(hits_per_page),
        "maxValuesPerFacet": "1000",
        "page": str(page),
        "query": "",
        "tagFilters": "",
    }
    return urlencode(params)


def build_visit_tricities_payload(page: int = 0, hits_per_page: int = DEFAULT_HITS_PER_PAGE) -> dict:
    """Build the Algolia multi-query payload for one VTC result page."""
    params = build_visit_tricities_params(page=page, hits_per_page=hits_per_page)
    return build_multi_query_payload(index_name=ALGOLIA_INDEX_NAME, params=params)
