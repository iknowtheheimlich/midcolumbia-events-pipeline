from __future__ import annotations

"""
Visit Tri-Cities source adapter placeholder.

This module intentionally does not pretend to have a working scraper yet.
The next implementation step is to inspect the live Visit Tri-Cities event pages
and determine whether they expose JSON-LD, an API endpoint, or rendered event
cards that require Playwright.

Keeping this adapter explicit prevents us from smuggling source-specific logic
into the CLI or Reddit exporter.
"""

from datetime import date
from cargo_harvester.models import EventRecord
from cargo_harvester.sources.base import SourceResult, LogFn

SOURCE_NAME = "Visit Tri-Cities"


async def harvest_visit_tricities(city: str, start: date, end: date, headless: bool = True, log: LogFn | None = None) -> SourceResult:
    if log:
        log("Visit Tri-Cities adapter is registered but not implemented yet.")
    return SourceResult(source_name=SOURCE_NAME, events=[], debug=[])
