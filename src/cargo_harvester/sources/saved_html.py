from __future__ import annotations

import re
from pathlib import Path

from cargo_harvester.models import clean_text
from cargo_harvester.sources.allevents import is_probable_event_url

URL_PATTERN = re.compile(r"https?://allevents\.in/[^\s\"'<>]+", re.I)


def extract_event_cards_from_html(path: Path) -> list[dict[str, str]]:
    html = path.read_text(encoding="utf-8", errors="ignore")
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    for match in URL_PATTERN.finditer(html):
        url = clean_text(match.group(0)).split("?")[0].rstrip("/")
        url = url.replace("&amp;", "&")
        if not url or url in seen:
            continue
        if not is_probable_event_url(url):
            continue
        seen.add(url)
        out.append({
            "url": url,
            "listing_text": "",
            "listing_image_url": "",
            "harvest_date": "",
            "harvest_url": str(path),
        })

    return out


def load_saved_html_folder(folder: Path) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for path in sorted(folder.glob("*.html")):
        cards.extend(extract_event_cards_from_html(path))
    return cards
