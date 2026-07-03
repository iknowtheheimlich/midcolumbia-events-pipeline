from __future__ import annotations

import csv
from pathlib import Path

from cargo_harvester.models import EventRecord, clean_text

FIELD_MAP = {
    "event_name": ["Event Name", "event_name", "title", "Title", "Name"],
    "date_raw": ["Date Raw", "date_raw", "date", "Date"],
    "start_time": ["Start Time", "start_time", "time", "Time"],
    "end_time": ["End Time", "end_time"],
    "venue": ["Venue", "venue", "location", "Location"],
    "city": ["City", "city"],
    "address": ["Address", "address"],
    "source": ["Source", "source"],
    "source_url": ["Source URL", "source_url", "url", "URL", "Link", "link"],
    "category": ["Category", "category"],
    "cost": ["Cost", "cost", "Price", "price"],
    "description": ["Description", "description", "Details", "details"],
    "image_url": ["Image URL", "image_url", "image", "Image"],
}


def get_value(row: dict[str, str], field: str) -> str:
    for key in FIELD_MAP[field]:
        if key in row and clean_text(row[key]):
            return clean_text(row[key])
    return ""


def load_manual_csv(path: Path, default_source: str = "Manual CSV") -> list[EventRecord]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        events = []
        for row in reader:
            event = EventRecord(
                event_name=get_value(row, "event_name"),
                date_raw=get_value(row, "date_raw"),
                start_time=get_value(row, "start_time"),
                end_time=get_value(row, "end_time"),
                venue=get_value(row, "venue"),
                city=get_value(row, "city"),
                address=get_value(row, "address"),
                source=get_value(row, "source") or default_source,
                source_url=get_value(row, "source_url"),
                category=get_value(row, "category"),
                cost=get_value(row, "cost"),
                description=get_value(row, "description"),
                image_url=get_value(row, "image_url"),
            )
            events.append(event.finalize())
    return events
