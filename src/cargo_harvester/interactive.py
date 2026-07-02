from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from cargo_harvester.core import dedupe_events, write_debug_json, write_events_csv
from cargo_harvester.reddit import build_reddit_weekly_draft
from cargo_harvester.sources.allevents import detail_to_event, is_probable_event_url, scrape_detail_pages


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


async def extract_visible_cards(page) -> list[dict[str, str]]:
    raw_cards: list[dict[str, Any]] = await page.evaluate(r'''
    () => {
        const out = [];
        const seen = new Set();
        function absUrl(url) { try { return new URL(url, location.href).href; } catch { return url || ""; } }
        function cardFor(el) {
            let cur = el;
            for (let i = 0; i < 8 && cur; i++) {
                const rect = cur.getBoundingClientRect ? cur.getBoundingClientRect() : null;
                const text = (cur.innerText || '').trim();
                if (text.length > 35 && rect && rect.width > 50 && rect.height > 20) return cur;
                cur = cur.parentElement;
            }
            return el;
        }
        function imgFor(card) {
            const imgs = Array.from(card.querySelectorAll ? card.querySelectorAll('img') : []);
            for (const img of imgs) {
                const url = absUrl(img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || '');
                if (url && !/logo|icon|avatar|default|blank|svg/i.test(url)) return url;
            }
            return '';
        }
        for (const a of Array.from(document.querySelectorAll('a[href]'))) {
            const href = absUrl(a.getAttribute('href') || a.href || '').split('?')[0].replace(/\/$/, '');
            if (!href.includes('allevents.in') || seen.has(href)) continue;
            seen.add(href);
            const card = cardFor(a);
            out.push({
                url: href,
                listing_text: (card.innerText || a.innerText || '').trim(),
                listing_image_url: imgFor(card),
                harvest_url: location.href,
                harvest_date: ''
            });
        }
        return out;
    }
    ''')

    cards: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_cards:
        url = str(raw.get("url", "")).strip()
        if not url or url in seen:
            continue
        if not is_probable_event_url(url):
            continue
        seen.add(url)
        cards.append({
            "url": url,
            "listing_text": str(raw.get("listing_text", "") or "").strip(),
            "listing_image_url": str(raw.get("listing_image_url", "") or "").strip(),
            "harvest_url": str(raw.get("harvest_url", "") or "").strip(),
            "harvest_date": str(raw.get("harvest_date", "") or "").strip(),
        })
    return cards


async def run(args) -> None:
    start = parse_date(args.start)
    end = parse_date(args.end)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug"

    profile_dir = Path(args.profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport={"width": 1400, "height": 1000},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)

        print("")
        print("Cargo Harvester Interactive Mode")
        print("--------------------------------")
        print("Browser is open.")
        print("Clear verification/login if needed.")
        print("Turn VPN off if AllEvents acts feral.")
        print("Select city/date/filters manually.")
        print("Scroll/load until the event cards you want are visible.")
        print("")
        input("When the correct page is visible, press ENTER here to harvest it...")

        cards = await extract_visible_cards(page)
        print(f"Visible event URLs discovered: {len(cards)}")

        details = await scrape_detail_pages(context, cards, start, end, print)
        events = dedupe_events([detail_to_event(detail, args.city) for detail in details])

        csv_path = output_dir / "unified_events.csv"
        reddit_path = output_dir / "reddit_weekly_draft.md"
        write_events_csv(events, csv_path)
        reddit_path.write_text(build_reddit_weekly_draft(events), encoding="utf-8")
        write_debug_json(details or cards, debug_dir / "interactive_cards.json")

        print("")
        print(f"Events written: {len(events)}")
        print(f"Rows needing review: {sum(1 for event in events if event.needs_review == 'Yes')}")
        print(f"CSV: {csv_path}")
        print(f"Reddit draft: {reddit_path}")
        print(f"Debug: {debug_dir / 'interactive_cards.json'}")
        await context.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive AllEvents harvester.")
    parser.add_argument("--city", default="richland-wa")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", default="output")
    parser.add_argument("--profile-dir", default="browser_profile")
    parser.add_argument("--url", default="https://allevents.in/richland-wa/all")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
