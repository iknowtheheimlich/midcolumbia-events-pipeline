"""Canonical identity and deterministic mission numbering for Mid-Columbia Mission Control."""

from __future__ import annotations

from datetime import date, datetime

PROJECT_NAME = "Mid-Columbia Mission Control"
MISSION_FLOW = "Discover → Curate → Verify → Publish"
MISSION_PREFIX = "MC"


def mission_id_for_week(week_start: str | date) -> str:
    """Return a stable mission ID using the ISO week of the mission start date."""
    value = week_start if isinstance(week_start, date) else datetime.strptime(week_start, "%Y-%m-%d").date()
    iso = value.isocalendar()
    return f"{MISSION_PREFIX}-{iso.year}-{iso.week:03d}"
