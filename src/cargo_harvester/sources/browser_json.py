from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cargo_harvester.models import clean_text
from cargo_harvester.sources.allevents import is_probable_event_url


def normalize_card(raw: dict[str, Any], source_path: Path) -> dict[str, str]:
    return {
        "url": clean_text(raw.get("url")),
        "listing_text": clean_text(raw.get("listing_text")),
        "listing_image_url": clean_text(raw.get("listing_image_url")),
        "harvest_date": clean_text(raw.get("harvest_date")),
        "harvest_url": clean_text(raw.get("collector_url") or raw.get("harvest_url") or source_path),
    }


def load_browser_json_file(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_events = data.get("events", data if isinstance(data, list) else [])
    cards: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        card = normalize_card(raw, path)
        url = card.get("url", "")
        if not url or url in seen:
            continue
        if not is_probable_event_url(url):
            continue
        seen.add(url)
        cards.append(card)

    return cards


def load_browser_json_folder(folder: Path) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for path in sorted(folder.glob("*.json")):
        cards.extend(load_browser_json_file(path))
    return cards
