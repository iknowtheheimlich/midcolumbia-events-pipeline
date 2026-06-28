from __future__ import annotations

"""
Visit Tri-Cities rendered-page adapter.

The events page is JavaScript-driven, so this adapter uses Playwright and a
conservative rendered-card extraction strategy. It is intentionally less
aggressive than the AllEvents adapter until we validate live output locally.
"""

import re
from datetime import date
from typing import Any

from playwright.async_api import async_playwright

from cargo_harvester.models import EventRecord, clean_text
from cargo_harvester.sources.base import SourceResult, LogFn

SOURCE_NAME = "Visit Tri-Cities"
EVENTS_URL = "https://www.visittri-cities.com/events/"
TRI_CITIES = ["Kennewick", "Richland", "Pasco", "West Richland", "Benton City", "Burbank", "Finley"]


async def auto_scroll(page, max_scrolls: int = 10) -> None:
    last_height = 0
    stable_count = 0
    for _ in range(max_scrolls):
        height = await page.evaluate("document.body.scrollHeight")
        stable_count = stable_count + 1 if height == last_height else 0
        if stable_count >= 3:
            break
        last_height = height
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)


async def extract_rendered_cards(page) -> list[dict[str, str]]:
    return await page.evaluate(r'''
    () => {
        const out = [];
        const seen = new Set();
        const anchors = Array.from(document.querySelectorAll('a[href]'));

        function absUrl(url) {
            try { return new URL(url, location.href).href; } catch { return url || ''; }
        }

        function looksLikeEventUrl(url) {
            if (!url) return false;
            if (!url.includes('visittri-cities.com')) return false;
            if (/\/events\//i.test(url) && !/\/events\/?($|#|\?)/i.test(url)) return true;
            return false;
        }

        function findCard(el) {
            let cur = el;
            for (let i = 0; i < 8 && cur; i++) {
                const text = (cur.innerText || '').trim();
                const imgCount = cur.querySelectorAll ? cur.querySelectorAll('img').length : 0;
                if (text.length > 30 && imgCount >= 1) return cur;
                cur = cur.parentElement;
            }
            return el;
        }

        function findImage(card) {
            const imgs = Array.from(card.querySelectorAll ? card.querySelectorAll('img') : []);
            const candidates = imgs.map(img =>
                img.currentSrc || img.src || img.getAttribute('data-src') ||
                img.getAttribute('data-original') || img.getAttribute('data-lazy') || ''
            )
            .filter(Boolean)
            .map(absUrl)
            .filter(url => !/logo|icon|avatar|blank|svg/i.test(url));
            return candidates[0] || '';
        }

        for (const a of anchors) {
            const href = absUrl(a.getAttribute('href') || a.href || '');
            if (!looksLikeEventUrl(href)) continue;
            const cleanHref = href.split('#')[0];
            if (seen.has(cleanHref)) continue;
            seen.add(cleanHref);

            const card = findCard(a);
            const text = (card.innerText || a.innerText || '').trim();
            if (text.length < 20) continue;

            out.push({
                url: cleanHref,
                text,
                image_url: findImage(card),
                html_class: card.className || '',
            });
        }
        return out;
    }
    ''')


def parse_card_text(text: str, fallback_date: str = "") -> dict[str, str]:
    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    joined = clean_text(text)

    date_raw = fallback_date
    start_time = ""
    end_time = ""
    venue = ""
    city = ""
    title = ""

    for pattern in [
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]:
        match = re.search(pattern, joined)
        if match:
            date_raw = clean_text(match.group(0))
            break

    for pattern in [
        r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\s*(?:-|–|to)?\s*\d{0,2}(?::?\d{0,2})?\s*(?:AM|PM|am|pm)?\b",
        r"\bAll day\b",
    ]:
        match = re.search(pattern, joined)
        if match:
            raw_time = clean_text(match.group(0))
            parts = re.split(r"\s*(?:-|–|to)\s*", raw_time, maxsplit=1)
            start_time = clean_text(parts[0])
            if len(parts) > 1:
                end_time = clean_text(parts[1])
            break

    noise = ["save", "share", "view event", "learn more", "details", "calendar"]
    for line in lines:
        lower = line.lower()
        if any(word in lower for word in noise):
            continue
        if date_raw and date_raw.lower() in lower:
            continue
        if start_time and start_time.lower() in lower:
            continue
        if len(line) >= 5:
            title = line
            break

    for c in TRI_CITIES:
        if re.search(rf"\b{re.escape(c)}\b", joined, re.I):
            city = c
            break

    for line in lines:
        if city and city.lower() in line.lower():
            venue = line
            break

    return {
        "title": title,
        "date_raw": date_raw,
        "start_time": start_time,
        "end_time": end_time,
        "venue": venue,
        "city": city,
        "description": joined[:1500],
    }


def card_to_event(card: dict[str, str], fallback_date: str) -> EventRecord:
    parsed = parse_card_text(card.get("text", ""), fallback_date=fallback_date)
    event = EventRecord(
        event_name=parsed["title"],
        date_raw=parsed["date_raw"],
        start_time=parsed["start_time"],
        end_time=parsed["end_time"],
        venue=parsed["venue"],
        city=parsed["city"],
        source=SOURCE_NAME,
        source_url=clean_text(card.get("url")),
        description=parsed["description"],
        image_url=clean_text(card.get("image_url")),
        harvest_date=fallback_date,
        harvest_url=EVENTS_URL,
    )
    return event.finalize()


async def harvest_visit_tricities(city: str, start: date, end: date, headless: bool = True, log: LogFn | None = None) -> SourceResult:
    if log:
        log("Visit Tri-Cities: rendering events page")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        )
        page = await context.new_page()
        await page.goto(EVENTS_URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        await auto_scroll(page)
        cards = await extract_rendered_cards(page)
        await browser.close()

    # The rendered page controls its own listing/filter UI. Until we locate a stable
    # API endpoint, retain the harvest start date as a fallback/debug field.
    fallback_date = start.isoformat()
    events = [card_to_event(card, fallback_date=fallback_date) for card in cards]

    if log:
        log(f"Visit Tri-Cities: {len(events)} rendered cards")

    return SourceResult(source_name=SOURCE_NAME, events=events, debug=cards)
