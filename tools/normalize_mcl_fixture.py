"""Normalize Mid-Columbia Libraries raw HTML fixture."""

from __future__ import annotations

import json
from pathlib import Path

from adapters.mcl.parser import parse_listing_html

RAW_PATH = Path("fixtures/mcl/raw_events.html")
OUTPUT_PATH = Path("fixtures/mcl/normalized_events.json")
YEAR = 2026


def main() -> None:
    html = RAW_PATH.read_text(encoding="utf-8")
    events = parse_listing_html(html, year=YEAR)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(events, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Parsed: {len(events)}")
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()