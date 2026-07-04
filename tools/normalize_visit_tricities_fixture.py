"""Normalize a saved Visit Tri-Cities Algolia fixture.

Usage:
    python tools/normalize_visit_tricities_fixture.py

Reads:
    fixtures/visit_tricities/api_events_search.json

Writes:
    fixtures/visit_tricities/normalized_events.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from adapters.visit_tricities.adapter import parse_visit_tricities_payload

DEFAULT_INPUT = Path("fixtures/visit_tricities/api_events_search.json")
DEFAULT_OUTPUT = Path("fixtures/visit_tricities/normalized_events.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Visit Tri-Cities fixture")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input Algolia JSON fixture")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output normalized JSON path")
    args = parser.parse_args()

    payload = load_json_fixture(args.input)
    events = parse_visit_tricities_payload(payload)
    save_json_fixture(args.output, events)
    print(f"Wrote {len(events)} normalized events: {args.output}")


if __name__ == "__main__":
    main()
