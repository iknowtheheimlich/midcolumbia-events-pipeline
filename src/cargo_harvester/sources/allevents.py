from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Callable

from playwright.async_api import async_playwright

from cargo_harvester.models import EventRecord, clean_text

TRI_CITIES = ["Kennewick", "Richland", "Pasco", "West Richland", "Benton City", "Burbank", "Finley"]


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_candidate_urls(city: str, day: date) -> list[str]:
    city = city.strip("/").lower()
    iso = day.isoformat()
    ymd = day.strftime("%Y%m%d")
    month = day.strftime("%B").lower()
    return [
        f"https://allevents.in/{city}/all?ref=cityhome_tab&date={iso}",
        f"https://allevents.in/{city}/all?date={iso}",
        f"https://allevents.in/{city}/all?from={iso}&to={iso}",
        f"https://allevents.in/{city}/all?start_date={iso}&end_date={iso}",
        f"https://allevents.in/{city}/events?date={iso}",
        f"https://allevents.in/{city}/{iso}",
        f"https://allevents.in/{city}/{ymd}",
        f"https://allevents.in/{city}/{month}-{day.day}",
    ]


async def auto_scroll(page, max_scrolls: int = 12) -> None:
    last_height = 0
    stable_count = 0
    for _ in range(max_scrolls):
        height = await page.evaluate("document.body.scrollHeight")
        stable_count = stable_count + 1 if height == last_height else 0
        if stable_count >= 3:
            break
        last_height = height
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(900)


async def extract_cards(page) -> list[dict[str, str]]:
    return await page.evaluate(r'''
    () => {
        const anchors = Array.from(document.querySelectorAll('a[href*="allevents.in"]'));
        const out = [];
        const seen = new Set();

        function absUrl(url) {
            try { return new URL(url, location.href).href; } catch { return url || ""; }
        }
        function looksLikeEventUrl(url) {
            if (!url) return false;
            if (/allevents\.in\/.+\/\d{8,}/.test(url)) return true;
            if (/allevents\.in\/[^/]+\/[a-z0-9-]+/i.test(url)
                && !/\/all($|\?)|\/events($|\?)|\/tickets($|\?)/i.test(url)) return true;
            return false;
        }
        function findCard(el) {
            let cur = el;
            for (let i = 0; i < 8 && cur; i++) {
                const txt = (cur.innerText || "").trim();
                const imgs = cur.querySelectorAll ? cur.querySelectorAll("img").length : 0;
                if (txt.length > 35 && imgs >= 1) return cur;
                cur = cur.parentElement;
            }
            return el;
        }
        function findImage(card) {
            const imgs = Array.from(card.querySelectorAll ? card.querySelectorAll("img") : []);
            const candidates = imgs.map(img =>
                img.currentSrc || img.src || img.getAttribute("data-src") ||
                img.getAttribute("data-original") || img.getAttribute("data-lazy") || ""
            )
            .filter(Boolean)
            .map(absUrl)
            .filter(url => !/logo|icon|avatar|default|blank|svg/i.test(url));
            return candidates[0] || "";
        }

        for (const a of anchors) {
            const href = absUrl(a.getAttribute("href") || a.href || "");
            if (!looksLikeEventUrl(href)) continue;
            const cleanHref = href.split("?")[0].replace(/\/$/, "");
            if (seen.has(cleanHref)) continue;
            seen.add(cleanHref);
            const card = findCard(a);
            const text = (card.innerText || a.innerText || "").trim();
            if (text.length < 20) continue;
            out.push({ url: cleanHref, text, image_url: findImage(card), html_class: card.className || "" });
        }
        return out;
    }
    ''')


async def harvest_one_url(context, url: str) -> list[dict[str, str]]:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1800)
        await auto_scroll(page)
        return await extract_cards(page)
    except Exception:
        return []
    finally:
        await page.close()


async def harvest_date(context, city: str, day: date, log: Callable[[str], None] | None = None) -> list[dict[str, str]]:
    best_cards: list[dict[str, str]] = []
    best_url = ""
    for url in build_candidate_urls(city, day):
        cards = await harvest_one_url(context, url)
        if len(cards) > len(best_cards):
            best_cards = cards
            best_url = url
        if len(cards) >= 8:
            break
    for card in best_cards:
        card["harvest_date"] = day.isoformat()
        card["harvest_url"] = best_url
    if log:
        log(f"{day.isoformat()}: {len(best_cards)} cards")
    return best_cards


def parse_card_text(text: str) -> dict[str, str]:
    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    joined = clean_text(text)

    date_raw = ""
    start_time = ""
    end_time = ""
    venue = ""
    city = ""

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

    noise = ["interested", "share", "save", "followers", "going", "event starts"]
    title = ""
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

    return {"title": title, "date_raw": date_raw, "start_time": start_time, "end_time": end_time, "venue": venue, "city": city, "description": joined[:1500]}


def card_to_event(card: dict[str, str], fallback_city: str) -> EventRecord:
    parsed = parse_card_text(card.get("text", ""))
    event = EventRecord(
        event_name=parsed["title"],
        date_raw=parsed["date_raw"] or clean_text(card.get("harvest_date")),
        start_time=parsed["start_time"],
        end_time=parsed["end_time"],
        venue=parsed["venue"],
        city=parsed["city"] or fallback_city.title(),
        source="AllEvents",
        source_url=clean_text(card.get("url")),
        description=parsed["description"],
        image_url=clean_text(card.get("image_url")),
        harvest_date=clean_text(card.get("harvest_date")),
        harvest_url=clean_text(card.get("harvest_url")),
    )
    return event.finalize()


async def harvest_allevents(city: str, start: date, end: date, headless: bool = True, log: Callable[[str], None] | None = None) -> tuple[list[EventRecord], list[dict[str, str]]]:
    all_cards: list[dict[str, str]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        )
        for day in iter_dates(start, end):
            all_cards.extend(await harvest_date(context, city, day, log))
        await browser.close()
    return [card_to_event(card, city) for card in all_cards], all_cards
