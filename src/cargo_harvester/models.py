from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

CANONICAL_FIELDS = [
    "Event Name", "Date Raw", "Start Time", "End Time", "Venue", "City", "Address",
    "Source", "Source URL", "Category", "Cost", "Description", "Image URL",
    "About Date Claim", "About Time Claim", "Date Conflict", "Time Conflict",
    "Harvest Date", "Harvest URL", "Status", "Reddit Include", "Needs Review",
    "Review Notes", "Dedupe Key",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


@dataclass
class EventRecord:
    event_name: str = ""
    date_raw: str = ""
    start_time: str = ""
    end_time: str = ""
    venue: str = ""
    city: str = ""
    address: str = ""
    source: str = "AllEvents"
    source_url: str = ""
    category: str = ""
    cost: str = ""
    description: str = ""
    image_url: str = ""
    about_date_claim: str = ""
    about_time_claim: str = ""
    date_conflict: str = "No"
    time_conflict: str = "No"
    harvest_date: str = ""
    harvest_url: str = ""
    status: str = "Raw"
    reddit_include: str = "Yes"
    needs_review: str = "No"
    review_notes: str = ""
    dedupe_key: str = ""

    def finalize(self) -> "EventRecord":
        notes = []
        existing_notes = clean_text(self.review_notes)
        if existing_notes:
            notes.append(existing_notes)
        if not self.event_name:
            notes.append("Missing event name")
        if not self.date_raw:
            notes.append("Missing date")
        if not self.source_url:
            notes.append("Missing source URL")
        if not self.image_url:
            notes.append("Missing image URL")
        if not self.start_time:
            notes.append("Missing start time")
        if not self.venue:
            notes.append("Missing venue")
        if self.date_conflict == "Yes":
            notes.append("Structured date conflicts with About section")
        if self.time_conflict == "Yes":
            notes.append("Structured time conflicts with About section")
        self.needs_review = "Yes" if notes else "No"
        self.review_notes = "; ".join(dict.fromkeys(notes))
        if not self.dedupe_key:
            self.dedupe_key = make_dedupe_key(self)
        return self

    def to_csv_row(self) -> dict[str, str]:
        return {
            "Event Name": self.event_name,
            "Date Raw": self.date_raw,
            "Start Time": self.start_time,
            "End Time": self.end_time,
            "Venue": self.venue,
            "City": self.city,
            "Address": self.address,
            "Source": self.source,
            "Source URL": self.source_url,
            "Category": self.category,
            "Cost": self.cost,
            "Description": self.description,
            "Image URL": self.image_url,
            "About Date Claim": self.about_date_claim,
            "About Time Claim": self.about_time_claim,
            "Date Conflict": self.date_conflict,
            "Time Conflict": self.time_conflict,
            "Harvest Date": self.harvest_date,
            "Harvest URL": self.harvest_url,
            "Status": self.status,
            "Reddit Include": self.reddit_include,
            "Needs Review": self.needs_review,
            "Review Notes": self.review_notes,
            "Dedupe Key": self.dedupe_key,
        }


def make_dedupe_key(event: EventRecord) -> str:
    raw = "|".join(clean_text(x).lower() for x in [
        event.event_name, event.date_raw, event.start_time, event.venue, event.city, event.source_url
    ])
    return re.sub(r"[^a-z0-9|]+", "", raw)


def is_fatal(event: EventRecord) -> bool:
    notes = event.review_notes or ""
    return any(x in notes for x in ["Missing event name", "Missing date", "Missing source URL"])
