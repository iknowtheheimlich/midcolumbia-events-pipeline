"""Fetch Visit Tri-Cities Algolia events and save a fixture.

Usage:
    python tools/fetch_visit_tricities_fixture.py --page 0

This tool uses the public browser Algolia credentials shipped by Visit Tri-Cities.
Environment overrides:
    VTC_ALGOLIA_APP_ID
    VTC_ALGOLIA_API_KEY
    VTC_ALGOLIA_INDEX_NAME
    VTC_ALGOLIA_MULTI_QUERY_URL
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.client import fetch_multi_query
from adapters.algolia.fixtures import save_json_fixture
from adapters.visit_tricities.config import (
    ALGOLIA_API_KEY,
    ALGOLIA_APP_ID,
    ALGOLIA_MULTI_QUERY_URL,
)
from adapters.visit_tricities.request import build_visit_tricities_payload

DEFAULT_OUTPUT = Path("fixtures/visit_tricities/api_events_search.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Visit Tri-Cities Algolia fixture")
    parser.add_argument("--page", type=int, default=0, help="Algolia result page")
    parser.add_argument("--hits-per-page", type=int, default=24, help="Hits per page")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output fixture path")
    args = parser.parse_args()

    payload = build_visit_tricities_payload(page=args.page, hits_per_page=args.hits_per_page)
    response = fetch_multi_query(
        url=ALGOLIA_MULTI_QUERY_URL,
        app_id=ALGOLIA_APP_ID,
        api_key=ALGOLIA_API_KEY,
        payload=payload,
    )
    save_json_fixture(args.output, response)
    print(f"Saved fixture: {args.output}")


if __name__ == "__main__":
    main()
