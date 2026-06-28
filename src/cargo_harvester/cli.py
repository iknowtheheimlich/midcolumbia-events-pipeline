from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from cargo_harvester.core import dedupe_events, write_events_csv
from cargo_harvester.reddit import build_reddit_weekly_draft
from cargo_harvester.sources.allevents import harvest_allevents


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


async def run(args) -> None:
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    events, cards = await harvest_allevents(
        city=args.city,
        start=parse_date(args.start),
        end=parse_date(args.end),
        headless=not args.visible,
        log=print,
    )
    events = dedupe_events(events)

    csv_path = output_dir / "unified_events.csv"
    reddit_path = output_dir / "reddit_weekly_draft.md"

    write_events_csv(events, csv_path)
    reddit_path.write_text(build_reddit_weekly_draft(events), encoding="utf-8")

    print("")
    print(f"Events written: {len(events)}")
    print(f"CSV: {csv_path}")
    print(f"Reddit draft: {reddit_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest Mid-Columbia event listings.")
    parser.add_argument("--city", default="kennewick")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", default="output")
    parser.add_argument("--visible", action="store_true", help="Show browser while harvesting")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
