from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from cargo_harvester.core import dedupe_events, write_events_csv, write_debug_json
from cargo_harvester.reddit import build_reddit_weekly_draft
from cargo_harvester.sources.allevents import harvest_allevents, scrape_detail_pages, detail_to_event
from cargo_harvester.sources.manual_csv import load_manual_csv
from cargo_harvester.sources.saved_html import load_saved_html_folder
from cargo_harvester.sources.visit_tricities import harvest_visit_tricities
from playwright.async_api import async_playwright


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


async def scrape_saved_html_details(cards, start, end, headless: bool, profile_dir: Path | None):
    async with async_playwright() as p:
        if profile_dir:
            profile_dir.mkdir(parents=True, exist_ok=True)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=headless,
                viewport={"width": 1400, "height": 1000},
            )
            details = await scrape_detail_pages(context, cards, start, end, print)
            await context.close()
            return details

        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        details = await scrape_detail_pages(context, cards, start, end, print)
        await browser.close()
        return details


async def run(args) -> None:
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug"

    events = []
    start = parse_date(args.start)
    end = parse_date(args.end)

    profile_dir = Path(args.profile_dir) if args.profile_dir else None
    if profile_dir:
        print(f"Browser profile: {profile_dir}")

    if args.saved_html:
        saved_folder = Path(args.saved_html)
        cards = load_saved_html_folder(saved_folder)
        print(f"Saved HTML cards discovered: {len(cards)}")
        details = await scrape_saved_html_details(cards, start, end, headless=not args.visible, profile_dir=profile_dir)
        events.extend(detail_to_event(detail, args.city) for detail in details)
        if args.debug:
            write_debug_json(details or cards, debug_dir / "saved_html_cards.json")

    if not args.skip_allevents and not args.saved_html:
        allevents_events, allevents_cards = await harvest_allevents(
            city=args.city,
            start=start,
            end=end,
            headless=not args.visible,
            log=print,
            profile_dir=profile_dir,
        )
        events.extend(allevents_events)
        if args.debug:
            write_debug_json(allevents_cards, debug_dir / "allevents_cards.json")

    if args.visit_tricities:
        visit_result = await harvest_visit_tricities(
            city=args.city,
            start=start,
            end=end,
            headless=not args.visible,
            log=print,
        )
        events.extend(visit_result.events)
        if args.debug:
            write_debug_json(visit_result.debug or [], debug_dir / "visit_tricities_cards.json")

    for manual_csv in args.manual_csv:
        manual_path = Path(manual_csv)
        print(f"Manual CSV: {manual_path}")
        events.extend(load_manual_csv(manual_path))

    events = dedupe_events(events)

    csv_path = output_dir / "unified_events.csv"
    reddit_path = output_dir / "reddit_weekly_draft.md"

    write_events_csv(events, csv_path)
    reddit_path.write_text(build_reddit_weekly_draft(events), encoding="utf-8")

    review_count = sum(1 for event in events if event.needs_review == "Yes")

    print("")
    print(f"Events written: {len(events)}")
    print(f"Rows needing review: {review_count}")
    print(f"CSV: {csv_path}")
    print(f"Reddit draft: {reddit_path}")
    if args.debug:
        print(f"Debug folder: {debug_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest Mid-Columbia event listings.")
    parser.add_argument("--city", default="kennewick")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", default="output")
    parser.add_argument("--visible", action="store_true", help="Show browser while harvesting")
    parser.add_argument("--debug", action="store_true", help="Write raw source debug JSON files")
    parser.add_argument("--profile-dir", default="", help="Persistent local browser profile directory for login/session reuse")
    parser.add_argument("--saved-html", default="", help="Folder containing saved AllEvents HTML pages")
    parser.add_argument("--skip-allevents", action="store_true", help="Only use manual/source files")
    parser.add_argument("--visit-tricities", action="store_true", help="Include rendered Visit Tri-Cities event listings")
    parser.add_argument("--manual-csv", action="append", default=[], help="Additional CSV file to merge into the unified event feed")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
