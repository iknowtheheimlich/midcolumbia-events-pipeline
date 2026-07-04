"""Richland Library LibCal request builder."""

from __future__ import annotations

from urllib.parse import urlencode

from adapters.richland_library.config import CALENDAR_CONTEXT, CALENDAR_ID, MONTHLY_ENDPOINT


def build_monthly_url(date: str) -> str:
    """Build the Richland Library LibCal monthly AJAX URL."""
    params = {
        "id": CALENDAR_ID,
        "c": CALENDAR_CONTEXT,
        "date": date,
        "monthly": "0",
        "audience": "",
        "cats": "undefined",
        "camps": "undefined",
    }
    return f"{MONTHLY_ENDPOINT}?{urlencode(params)}"
