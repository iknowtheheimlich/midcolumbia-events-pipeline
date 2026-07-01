from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from cargo_harvester.models import EventRecord, clean_text

TRI_CITIES = ["Kennewick", "Richland", "Pasco", "West Richland", "Benton City", "Burbank", "Finley"]

CATEGORY_SLUGS = {
    "music", "concerts", "parties", "performances", "comedy", "dance", "entertainment", "fine-arts",
    "theatre", "theater", "literary-art", "crafts", "photography", "cooking", "arts", "food-drinks",
    "business", "festivals", "meetups", "sports", "workshops", "webinars", "kids", "health-wellness",
    "trips-adventures", "4th-of-july", "best-events-this-weekend",
}

SYSTEM_SLUGS = {
    "all", "events", "tickets", "calendar", "signin", "login", "signup", "help", "support", "about",
    "organizer", "create-event", "add-event", "pricing", "sell-tickets",
}


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
    base = [
        f"https://allevents.in/{city}/all?ref=cityhome_tab&date={iso}",
        f"https://allevents.in/{city}/all?date={iso}",
        f"https://allevents.in/{city}/all?from={iso}&to={iso}",
        f"https://allevents.in/{city}/all?start_date={iso}&end_date={iso}",
        f"https://allevents.in/{city}/events?date={iso}",
        f"https://allevents.in/{city}/{iso}",
        f"https://allevents.in/{city}/{ymd}",
        f"https://allevents.in/{city}/{month}-{day.day}",
    ]
    category_pages = [f"https://allevents.in/{city}/{slug}" for slug in sorted(CATEGORY_SLUGS)]
    return base + category_pages


def url_parts(url: str) -> list[str]:
    return [p for p in urlparse(url).path.strip("/").split("/") if p]


def is_allevents_url(url: str) -> bool:
    return urlparse(url).netloc.endswith("allevents.in")


def is_category_url(url: str) -> bool:
    parts = url_parts(url)
    return len(parts) >= 2 and parts[-1].lower() in CATEGORY_SLUGS


def is_system_url(url: str) -> bool:
    parts = url_parts(url)
    return len(parts) < 2 or any(piece.lower() in SYSTEM_SLUGS for piece in parts[1:])


def is_probable_event_url(url: str) -> bool:
    if not is_allevents_url(url) or is_system_url(url) or is_category_url(url):
        return False
    parts = url_parts(url)
    slug = parts[-1].lower()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d{8}", slug):
        return False
    if not re.search(r"[a-z]", slug):
        return False
    return bool(re.search(r"\d{6,}", url) or len(slug) >= 12)


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


async def extract_links(page) -> list[dict[str, str]]:
    return await page.evaluate(r'''
    () => {
        const out = [];
        const seen = new Set();
        function absUrl(url) { try { return new URL(url, location.href).href; } catch { return url || ""; } }
        function cardFor(el) {
            let cur = el;
            for (let i = 0; i < 8 && cur; i++) {
                const text = (cur.innerText || '').trim();
                if (text.length > 35) return cur;
                cur = cur.parentElement;
            }
            return el;
        }
        function imgFor(card) {
            const imgs = Array.from(card.querySelectorAll ? card.querySelectorAll('img') : []);
            for (const img of imgs) {
                const url = absUrl(img.currentSrc || img.src || img.getAttribute('data-src') || '');
                if (url && !/logo|icon|avatar|default|blank|svg/i.test(url)) return url;
            }
            return '';
        }
        for (const a of Array.from(document.querySelectorAll('a[href]'))) {
            const href = absUrl(a.getAttribute('href') || a.href || '').split('?')[0].replace(/\/$/, '');
            if (!href.includes('allevents.in') || seen.has(href)) continue;
            seen.add(href);
            const card = cardFor(a);
            out.push({ url: href, listing_text: (card.innerText || a.innerText || '').trim(), listing_image_url: imgFor(card) });
        }
        return out;
    }
    ''')


async def harvest_listing_url(context, url: str) -> list[dict[str, str]]:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1800)
        await auto_scroll(page)
        return await extract_links(page)
    except Exception:
        return []
    finally:
        await page.close()


async def discover_date_urls(context, city: str, day: date, log: Callable[[str], None] | None = None) -> list[dict[str, str]]:
    event_cards: list[dict[str, str]] = []
    discovery_pages: list[str] = []
    seen_events: set[str] = set()
    seen_discovery: set[str] = set()

    for source_url in build_candidate_urls(city, day):
        links = await harvest_listing_url(context, source_url)
        for card in links:
            url = clean_text(card.get("url"))
            if not url or is_system_url(url):
                continue
            if is_probable_event_url(url) and url not in seen_events:
                seen_events.add(url)
                card["harvest_date"] = day.isoformat()
                card["harvest_url"] = source_url
                event_cards.append(card)
            elif is_category_url(url) and url not in seen_discovery:
                seen_discovery.add(url)
                discovery_pages.append(url)

    # Category pages are discovery ponds, not fish. Open them, but only keep event URLs found inside.
    for discovery_url in discovery_pages[:40]:
        links = await harvest_listing_url(context, discovery_url)
        for card in links:
            url = clean_text(card.get("url"))
            if is_probable_event_url(url) and url not in seen_events:
                seen_events.add(url)
                card["harvest_date"] = day.isoformat()
                card["harvest_url"] = discovery_url
                event_cards.append(card)

    if log:
        log(f"{day.isoformat()}: discovery pages {len(discovery_pages)}, probable event URLs {len(event_cards)}")
    return event_cards


def parse_event_date(value: str) -> date | None:
    value = clean_text(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%a, %d %b, %Y", "%a, %d %B, %Y", "%d %b, %Y", "%d %B, %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_detail_text(text: str) -> dict[str, str]:
    text = clean_text(text)
    date_raw = ""
    start_time = ""
    end_time = ""
    venue = ""
    city = ""

    date_patterns = [
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s+\d{4}\b",
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            date_raw = clean_text(match.group(0))
            break

    time_match = re.search(r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\s*(?:-|–|to)?\s*\d{0,2}(?::?\d{0,2})?\s*(?:AM|PM|am|pm)?\b", text)
    if time_match:
        raw_time = clean_text(time_match.group(0))
        parts = re.split(r"\s*(?:-|–|to)\s*", raw_time, maxsplit=1)
        start_time = clean_text(parts[0])
        end_time = clean_text(parts[1]) if len(parts) > 1 else ""

    for candidate in TRI_CITIES:
        if re.search(rf"\b{re.escape(candidate)}\b", text, re.I):
            city = candidate
            break

    return {"date_raw": date_raw, "start_time": start_time, "end_time": end_time, "venue": venue, "city": city}


async def scrape_detail(context, listing_card: dict[str, str]) -> dict[str, Any]:
    page = await context.new_page()
    url = clean_text(listing_card.get("url"))
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1500)
        body_text = await page.evaluate("document.body.innerText || ''")
        title = await page.evaluate("(document.querySelector('h1') && document.querySelector('h1').innerText) || document.title || ''")
        image_url = await page.evaluate("(document.querySelector('meta[property=\"og:image\"]') && document.querySelector('meta[property=\"og:image\"]').content) || ''")
        parsed = parse_detail_text(body_text)
        return {
            "url": url,
            "title": clean_text(title),
            "body_text": clean_text(body_text)[:5000],
            "image_url": clean_text(image_url) or clean_text(listing_card.get("listing_image_url")),
            "listing_card": listing_card,
            **parsed,
        }
    finally:
        await page.close()


async def scrape_detail_pages(context, listing_cards: list[dict[str, str]], start: date, end: date, log: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
    details = []
    seen = set()
    for index, card in enumerate(listing_cards, start=1):
        url = clean_text(card.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        try:
            detail = await scrape_detail(context, card)
            event_date = parse_event_date(detail.get("date_raw", ""))
            detail["event_date"] = event_date.isoformat() if event_date else ""
            detail["filtered_out"] = bool(event_date and not (start <= event_date <= end))
            if not detail["filtered_out"]:
                details.append(detail)
            if log:
                status = "kept" if not detail["filtered_out"] else "filtered"
                log(f"  detail {index}/{len(listing_cards)}: {status} - {detail.get('title') or url}")
        except Exception as exc:
            if log:
                log(f"  detail {index}/{len(listing_cards)} failed: {type(exc).__name__} - {url}")
    return details


def detail_to_event(detail: dict[str, Any], fallback_city: str) -> EventRecord:
    listing = detail.get("listing_card", {}) or {}
    event = EventRecord(
        event_name=clean_text(detail.get("title")),
        date_raw=clean_text(detail.get("date_raw")),
        start_time=clean_text(detail.get("start_time")),
        end_time=clean_text(detail.get("end_time")),
        venue=clean_text(detail.get("venue")),
        city=clean_text(detail.get("city")) or fallback_city.title(),
        source="AllEvents",
        source_url=clean_text(detail.get("url")),
        description=clean_text(detail.get("body_text"))[:1500],
        image_url=clean_text(detail.get("image_url")),
        harvest_date=clean_text(listing.get("harvest_date")),
        harvest_url=clean_text(listing.get("harvest_url")),
    )
    return event.finalize()


async def harvest_allevents(
    city: str,
    start: date,
    end: date,
    headless: bool = True,
    log: Callable[[str], None] | None = None,
    profile_dir: str | Path | None = None,
) -> tuple[list[EventRecord], list[dict[str, Any]]]:
    listing_cards: list[dict[str, str]] = []
    detail_rows: list[dict[str, Any]] = []
    async with async_playwright() as p:
        if profile_dir:
            profile_path = Path(profile_dir)
            profile_path.mkdir(parents=True, exist_ok=True)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=headless,
                viewport={"width": 1400, "height": 1000},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            )
            for day in iter_dates(start, end):
                listing_cards.extend(await discover_date_urls(context, city, day, log))
            detail_rows = await scrape_detail_pages(context, listing_cards, start, end, log)
            await context.close()
        else:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={"width": 1400, "height": 1000},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            )
            for day in iter_dates(start, end):
                listing_cards.extend(await discover_date_urls(context, city, day, log))
            detail_rows = await scrape_detail_pages(context, listing_cards, start, end, log)
            await browser.close()

    debug_rows = detail_rows or [{"listing_only": True, **card} for card in listing_cards]
    return [detail_to_event(detail, city) for detail in detail_rows], debug_rows
