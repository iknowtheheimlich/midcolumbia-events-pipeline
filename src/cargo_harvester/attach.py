from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError, async_playwright

from cargo_harvester.core import dedupe_events, write_debug_json, write_events_csv
from cargo_harvester.reddit import build_reddit_weekly_draft
from cargo_harvester.sources.allevents import detail_to_event, is_probable_event_url, scrape_detail_pages

LOCAL_SECTION_KEYWORDS = ["kennewick", "richland", "pasco", "west richland", "tri-cities", "tricities"]
BLOCKED_SECTION_KEYWORDS = ["around the globe", "popular in", "nearby cities", "other cities", "explore events", "top organizers"]


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


async def wait_for_page_to_settle(page) -> None:
    for state in ("domcontentloaded", "networkidle"):
        try:
            await page.wait_for_load_state(state, timeout=5000)
        except PlaywrightTimeoutError:
            pass
    await page.wait_for_timeout(1000)


async def choose_page(context):
    pages = [p for p in context.pages if not p.is_closed()]
    allevents_pages = [p for p in pages if "allevents.in" in p.url]
    if allevents_pages:
        return allevents_pages[-1]
    if pages:
        return pages[-1]
    return await context.new_page()


async def evaluate_visible_cards(page) -> list[dict[str, Any]]:
    return await page.evaluate(r'''
    ({localKeywords, blockedKeywords}) => {
        const out = [];
        const seen = new Set();
        function clean(value) { return (value || '').replace(/\s+/g, ' ').trim(); }
        function absUrl(url) { try { return new URL(url, location.href).href; } catch { return url || ""; } }
        function cardFor(el) {
            let cur = el;
            for (let i = 0; i < 8 && cur; i++) {
                const rect = cur.getBoundingClientRect ? cur.getBoundingClientRect() : null;
                const text = clean(cur.innerText || '');
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
        function previousSectionText(card) {
            const cardTop = card.getBoundingClientRect().top + window.scrollY;
            const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,[class*="title" i],[class*="heading" i]'));
            let best = '';
            let bestTop = -Infinity;
            for (const h of headings) {
                const text = clean(h.innerText || h.textContent || '');
                if (!text || text.length > 140) continue;
                const top = h.getBoundingClientRect().top + window.scrollY;
                if (top <= cardTop && top > bestTop) {
                    best = text;
                    bestTop = top;
                }
            }
            return best;
        }
        function sectionDecision(sectionText, cardText) {
            const combined = (sectionText + ' ' + cardText).toLowerCase();
            const blocked = blockedKeywords.some(k => combined.includes(k));
            const local = localKeywords.some(k => combined.includes(k));
            if (blocked && !local) return 'blocked';
            if (local) return 'local';
            return 'unknown';
        }
        for (const a of Array.from(document.querySelectorAll('a[href]'))) {
            const href = absUrl(a.getAttribute('href') || a.href || '').split('?')[0].replace(/\/$/, '');
            if (!href.includes('allevents.in') || seen.has(href)) continue;
            seen.add(href);
            const card = cardFor(a);
            const cardText = clean(card.innerText || a.innerText || '');
            const sectionText = previousSectionText(card);
            const sectionDecisionValue = sectionDecision(sectionText, cardText);
            out.push({
                url: href,
                listing_text: cardText,
                listing_image_url: imgFor(card),
                harvest_url: location.href,
                harvest_date: '',
                section_text: sectionText,
                section_decision: sectionDecisionValue
            });
        }
        return out;
    }
    ''', {"localKeywords": LOCAL_SECTION_KEYWORDS, "blockedKeywords": BLOCKED_SECTION_KEYWORDS})


async def extract_visible_cards(page, local_only: bool = True) -> list[dict[str, str]]:
    raw_cards: list[dict[str, Any]] = []
    last_error = ""
    for attempt in range(1, 6):
        try:
            await wait_for_page_to_settle(page)
            raw_cards = await evaluate_visible_cards(page)
            break
        except PlaywrightError as exc:
            last_error = str(exc)
            print(f"Page changed while reading cards; retrying {attempt}/5...")
            await page.wait_for_timeout(1200)
    if not raw_cards and last_error:
        print(f"No raw cards. Last browser error: {last_error[:240]}")

    cards: list[dict[str, str]] = []
    seen: set[str] = set()
    rejected_section = 0
    for raw in raw_cards:
        url = str(raw.get("url", "")).strip()
        if not url or url in seen:
            continue
        if not is_probable_event_url(url):
            continue
        section_decision = str(raw.get("section_decision", "unknown") or "unknown")
        if local_only and section_decision == "blocked":
            rejected_section += 1
            continue
        seen.add(url)
        cards.append({
            "url": url,
            "listing_text": str(raw.get("listing_text", "") or "").strip(),
            "listing_image_url": str(raw.get("listing_image_url", "") or "").strip(),
            "harvest_url": str(raw.get("harvest_url", "") or "").strip(),
            "harvest_date": str(raw.get("harvest_date", "") or "").strip(),
            "section_text": str(raw.get("section_text", "") or "").strip(),
            "section_decision": section_decision,
        })
    if local_only:
        print(f"Section filter rejected probable non-local cards: {rejected_section}")
    return cards


async def run(args) -> None:
    start = parse_date(args.start)
    end = parse_date(args.end)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug"

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(args.cdp_url)
        context = browser.contexts[0]
        page = await choose_page(context)

        print("")
        print("Cargo Harvester Chrome Attach Mode")
        print("----------------------------------")
        print(f"Attached page: {page.url}")
        print("Use your normal Chrome. Load/filter AllEvents there first.")
        print("Then return here and press ENTER.")
        print("")
        input("When the correct Chrome tab is visible and stable, press ENTER to harvest it...")

        page = await choose_page(context)
        print(f"Harvesting page: {page.url}")
        cards = await extract_visible_cards(page, local_only=not args.include_global_sections)
        print(f"Visible event URLs discovered: {len(cards)}")
        if not cards:
            print("No event cards found. Make sure the AllEvents listing tab is loaded and active, then rerun attach mode.")
            await browser.close()
            return

        details = await scrape_detail_pages(context, cards, start, end, print)
        events = dedupe_events([detail_to_event(detail, args.city) for detail in details])

        csv_path = output_dir / "unified_events.csv"
        reddit_path = output_dir / "reddit_weekly_draft.md"
        write_events_csv(events, csv_path)
        reddit_path.write_text(build_reddit_weekly_draft(events), encoding="utf-8")
        write_debug_json(details or cards, debug_dir / "attach_cards.json")

        print("")
        print(f"Events written: {len(events)}")
        print(f"Rows needing review: {sum(1 for event in events if event.needs_review == 'Yes')}")
        print(f"CSV: {csv_path}")
        print(f"Reddit draft: {reddit_path}")
        print(f"Debug: {debug_dir / 'attach_cards.json'}")
        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Attach to an existing Chrome instance and harvest visible AllEvents cards.")
    parser.add_argument("--city", default="richland-wa")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", default="output")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--include-global-sections", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
