from __future__ import annotations

from collections import defaultdict
from cargo_harvester.models import EventRecord

CITY_ORDER = ["Kennewick", "Richland", "Pasco", "West Richland", "Benton City", "Burbank", "Finley"]


def include_in_reddit(event: EventRecord) -> bool:
    if event.reddit_include.lower() not in {"yes", "true", "1"}:
        return False
    if event.status.lower() in {"excluded", "posted"}:
        return False
    if "Missing event name" in event.review_notes:
        return False
    if "Missing date" in event.review_notes:
        return False
    if not event.source_url:
        return False
    return True


def sort_key(event: EventRecord):
    city_rank = CITY_ORDER.index(event.city) if event.city in CITY_ORDER else 99
    return (event.date_raw, event.start_time, city_rank, event.event_name)


def format_time(event: EventRecord) -> str:
    if event.start_time and event.end_time:
        return f"{event.start_time}–{event.end_time}"
    return event.start_time or "Time TBA"


def clean_venue(event: EventRecord) -> str:
    venue = event.venue or "Venue TBA"
    if event.city and venue.lower().endswith(", " + event.city.lower()):
        venue = venue[:-(len(event.city) + 2)].strip()
    return venue


def build_reddit_weekly_draft(events: list[EventRecord]) -> str:
    included = sorted([e for e in events if include_in_reddit(e)], key=sort_key)
    by_date: dict[str, list[EventRecord]] = defaultdict(list)
    for event in included:
        by_date[event.date_raw].append(event)

    lines: list[str] = []
    lines.append("# Tri-Cities Events")
    lines.append("")
    lines.append("This is not an all inclusive list. Events were extracted from AllEvents and will expand as more sources are added.")
    lines.append("")

    for date_raw, date_events in by_date.items():
        lines.append(f"## {date_raw}")
        lines.append("")
        for event in date_events:
            lines.append(f"- [{event.event_name}]({event.source_url}) | {clean_venue(event)}, {event.city or 'Tri-Cities'} | {format_time(event)}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
