"""Build a Visit Tri-Cities Algolia payload for local inspection.

Usage:
    python tools/build_visit_tricities_payload.py --page 0
"""

from __future__ import annotations

import argparse
import json

from adapters.visit_tricities.request import build_visit_tricities_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Visit Tri-Cities Algolia payload")
    parser.add_argument("--page", type=int, default=0, help="Algolia result page")
    parser.add_argument("--hits-per-page", type=int, default=24, help="Hits per page")
    args = parser.parse_args()

    payload = build_visit_tricities_payload(page=args.page, hits_per_page=args.hits_per_page)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
