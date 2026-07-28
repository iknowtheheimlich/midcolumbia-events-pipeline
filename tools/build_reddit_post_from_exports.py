"""Build the weekly Reddit post from separate dated and recurring CSV exports.

The dated export supplies one-time and multi-day events. The recurring export
supplies undated weekly templates. The ``Final Post Ready`` value is emitted
verbatim; this tool does not reconstruct event markdown.

Expected dated CSV columns:
    Date, Category, Event Name, Final Post Ready

Expected recurring CSV columns:
    Day (or Weekday), Category, Event Name, Final Post Ready

Optional dated CSV columns used to identify multi-day rows:
    Multi Days, Multi-Day, Multi Day, Event Type

Usage:
    python -m tools.build_reddit_post_from_exports \
        weekly_events.csv recurring_events.csv output.txt \
        --week-start 2026-07-27
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping

CATEGORY_ORDER = (
    "Events/Hangouts",
    "Classes/Workshops",
    "Music/Comedy",
    "Sports",
    "Restaurants/Bars/Wineries",
    "Art/Theater",
    "Trivia/Game Night",
    "Karaoke/Open Mic",
    "Fundraisers",
    "Markets",
    "Community Programs",
    "School District Event",
    "Tours",
    "Festivals/Fair",
    "Estate/Yard/Garage Sales",
    "Faith Based",
)

WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_TRUE_VALUES = {"1", "true", "yes", "y", "checked", "x"}


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date value: {value!r}")


def _weekday(value: str) -> str:
    normalized = value.strip().casefold()
    aliases = {day.casefold(): day for day in WEEKDAYS}
    aliases.update({day[:3].casefold(): day for day in WEEKDAYS})
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported weekday value: {value!r}") from exc


def _category_sort_key(category: str) -> tuple[int, str]:
    try:
        return CATEGORY_ORDER.index(category), ""
    except ValueError:
        return len(CATEGORY_ORDER), category.casefold()


def _is_multi_day(row: Mapping[str, str]) -> bool:
    for key in ("Multi Days", "Multi-Day", "Multi Day"):
        if _clean(row.get(key)).casefold() in _TRUE_VALUES:
            return True
    event_type = _clean(row.get("Event Type")).casefold()
    return event_type in {"multi-day", "multi day", "multiday"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return [dict(row) for row in reader]


def _append_grouped(lines: list[str], rows: Iterable[Mapping[str, str]]) -> None:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        category = _clean(row.get("Category"))
        ready = _clean(row.get("Final Post Ready"))
        if not ready:
            continue
        grouped[category].append(ready)

    for category in sorted(grouped, key=_category_sort_key):
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"**{category}**")
        lines.extend(grouped[category][0:1])
        for ready in grouped[category][1:]:
            lines.extend(("", ready))


def build_reddit_post(
    dated_rows: Iterable[Mapping[str, str]],
    recurring_rows: Iterable[Mapping[str, str]],
    week_start: date,
) -> str:
    """Return a Monday-through-Sunday Reddit post using separate data sources."""
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    dated_by_day: dict[date, dict[str, list[Mapping[str, str]]]] = defaultdict(
        lambda: {"events": [], "multi": []}
    )
    for row in dated_rows:
        raw_date = _clean(row.get("Date"))
        if not raw_date:
            continue
        event_date = _parse_date(raw_date)
        bucket = "multi" if _is_multi_day(row) else "events"
        dated_by_day[event_date][bucket].append(row)

    recurring_by_day: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in recurring_rows:
        raw_day = _clean(row.get("Day")) or _clean(row.get("Weekday"))
        if not raw_day:
            continue
        recurring_by_day[_weekday(raw_day)].append(row)

    lines: list[str] = []
    for offset, weekday in enumerate(WEEKDAYS):
        current = week_start + timedelta(days=offset)
        if lines:
            lines.append("")
        lines.append(f"# {weekday}, {current.strftime('%B')} {current.day}")

        sections = (
            ("Events", dated_by_day[current]["events"]),
            ("Multi-Day Events", dated_by_day[current]["multi"]),
            (f"Happening Every {weekday}", recurring_by_day[weekday]),
        )
        for heading, rows in sections:
            lines.extend(("", f"## {heading}", ""))
            _append_grouped(lines, rows)

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a Reddit-ready weekly post from dated and recurring CSV exports."
    )
    parser.add_argument("dated_csv", type=Path)
    parser.add_argument("recurring_csv", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--week-start", required=True, help="Monday in YYYY-MM-DD format")
    args = parser.parse_args()

    week_start = _parse_date(args.week_start)
    output = build_reddit_post(
        _read_csv(args.dated_csv),
        _read_csv(args.recurring_csv),
        week_start,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(f"Wrote Reddit post: {args.output}")


if __name__ == "__main__":
    main()
