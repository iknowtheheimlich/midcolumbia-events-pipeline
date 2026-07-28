"""Build the weekly Reddit post from dated and recurring Notion CSV exports."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

CATEGORY_ORDER: tuple[str, ...] = (
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

FOOTER = (
    "This is not an all inclusive list. Events were extracted from "
    "allevents.in, visittri-cities.com, tricityvibe.com."
)

WEEKLY_REQUIRED_COLUMNS = frozenset(
    {"Date", "Category", "Event Name", "Final Post Ready"}
)
RECURRING_REQUIRED_COLUMNS = frozenset(
    {"Days of the Week", "Category", "Event Name", "Final Post Ready"}
)

_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d")
_DAY_NAMES = tuple(
    (date(2026, 7, 27) + timedelta(days=offset)).strftime("%A")
    for offset in range(7)
)


class RedditPublishingError(ValueError):
    """Raised when an export cannot safely produce a publish-ready post."""


@dataclass(frozen=True)
class PublishingRow:
    category: str
    event_name: str
    final_post_ready: str


@dataclass(frozen=True)
class DatedPublishingRow(PublishingRow):
    start_date: date
    end_date: date | None = None


@dataclass(frozen=True)
class RecurringPublishingRow(PublishingRow):
    days_of_week: tuple[str, ...] = ()


def load_weekly_export(path: Path) -> list[DatedPublishingRow]:
    rows, fieldnames = _read_csv(path)
    _require_columns(path, fieldnames, WEEKLY_REQUIRED_COLUMNS)

    loaded: list[DatedPublishingRow] = []
    for line_number, row in enumerate(rows, start=2):
        if _is_empty_row(row):
            continue
        category, event_name, final = _publishing_values(path, line_number, row)
        start_date, end_date = parse_date_range(
            _required_value(path, line_number, row, "Date")
        )
        loaded.append(
            DatedPublishingRow(
                category=category,
                event_name=event_name,
                final_post_ready=final,
                start_date=start_date,
                end_date=end_date,
            )
        )
    return loaded


def load_recurring_export(path: Path) -> list[RecurringPublishingRow]:
    rows, fieldnames = _read_csv(path)
    _require_columns(path, fieldnames, RECURRING_REQUIRED_COLUMNS)

    loaded: list[RecurringPublishingRow] = []
    for line_number, row in enumerate(rows, start=2):
        if _is_empty_row(row):
            continue
        category, event_name, final = _publishing_values(path, line_number, row)
        day_text = _required_value(path, line_number, row, "Days of the Week")
        days = parse_days_of_week(day_text)
        loaded.append(
            RecurringPublishingRow(
                category=category,
                event_name=event_name,
                final_post_ready=final,
                days_of_week=days,
            )
        )
    return loaded


def build_weekly_reddit_post(
    weekly_rows: Iterable[DatedPublishingRow],
    recurring_rows: Iterable[RecurringPublishingRow],
    *,
    week_start: date,
    category_order: Sequence[str] = CATEGORY_ORDER,
    footer: str = FOOTER,
) -> str:
    """Render Monday-through-Sunday output with three independent buckets."""

    if week_start.strftime("%A") != "Monday":
        raise RedditPublishingError(
            f"week_start must be a Monday, got {week_start.isoformat()} "
            f"({week_start.strftime('%A')})"
        )

    category_rank = {category: index for index, category in enumerate(category_order)}

    # Materialize exactly once because callers may pass generators.
    dated = list(weekly_rows)
    recurring = list(recurring_rows)
    unknown = {
        row.category
        for row in [*dated, *recurring]
        if row.category not in category_rank
    }
    if unknown:
        names = ", ".join(sorted(unknown))
        raise RedditPublishingError(f"Unknown Reddit categories: {names}")

    week_days = tuple(week_start + timedelta(days=offset) for offset in range(7))

    one_time: dict[date, dict[str, list[str]]] = {
        day: defaultdict(list) for day in week_days
    }
    multi_day: dict[date, dict[str, list[str]]] = {
        day: defaultdict(list) for day in week_days
    }
    every_week: dict[str, dict[str, list[str]]] = {
        day_name: defaultdict(list) for day_name in _DAY_NAMES
    }

    for row in dated:
        if row.end_date is None:
            if row.start_date in one_time:
                one_time[row.start_date][row.category].append(row.final_post_ready)
            continue

        if row.end_date < row.start_date:
            raise RedditPublishingError(
                f"End date precedes start date for {row.event_name!r}"
            )
        for day in week_days:
            if row.start_date <= day <= row.end_date:
                multi_day[day][row.category].append(row.final_post_ready)

    for row in recurring:
        for day_name in row.days_of_week:
            every_week[day_name][row.category].append(row.final_post_ready)

    day_blocks: list[str] = []
    for day in week_days:
        sections: list[str] = []
        sections.append(_render_section("Events", one_time[day], category_order))
        sections.append(
            _render_section("Multi-Day Events", multi_day[day], category_order)
        )
        sections.append(
            _render_section(
                f"Happening Every {day.strftime('%A')}",
                every_week[day.strftime("%A")],
                category_order,
            )
        )
        populated = [section for section in sections if section]
        heading = f"# {day.strftime('%A, %B')} {day.day}"
        day_blocks.append("\n\n".join([heading, *populated]))

    output = "\n\n".join(day_blocks)
    if footer.strip():
        output += "\n\n" + footer.strip()
    return output.rstrip() + "\n"


def write_weekly_reddit_post(
    weekly_csv: Path,
    recurring_csv: Path,
    output_path: Path,
    *,
    week_start: date,
) -> Path:
    post = build_weekly_reddit_post(
        load_weekly_export(weekly_csv),
        load_recurring_export(recurring_csv),
        week_start=week_start,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(post, encoding="utf-8")
    return output_path


def parse_date_range(value: str) -> tuple[date, date | None]:
    normalized = value.strip()
    for separator in ("→", "->", " to "):
        if separator in normalized:
            start_text, end_text = normalized.split(separator, 1)
            return _parse_date(start_text.strip()), _parse_date(end_text.strip())

    # Notion sometimes exports a date range as "start – end".
    match = re.fullmatch(r"(.+?)\s+[–—]\s+(.+)", normalized)
    if match:
        return _parse_date(match.group(1)), _parse_date(match.group(2))

    return _parse_date(normalized), None


def parse_days_of_week(value: str) -> tuple[str, ...]:
    """Parse weekday labels without pretending ordinal/monthly rules are weekly."""

    normalized = value.strip()
    if not normalized:
        raise RedditPublishingError("Recurring row is missing Days of the Week")

    ordinal_pattern = re.compile(
        r"\b(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth|last)\b",
        re.IGNORECASE,
    )
    if ordinal_pattern.search(normalized):
        raise RedditPublishingError(
            f"{value!r} is not an every-week schedule; give it a dated occurrence "
            "in the weekly export instead"
        )

    found: list[str] = []
    for day_name in _DAY_NAMES:
        if re.search(rf"\b{day_name}s?\b", normalized, re.IGNORECASE):
            found.append(day_name)

    if not found:
        raise RedditPublishingError(
            f"Could not resolve a weekday from Days of the Week={value!r}"
        )
    return tuple(found)


def _render_section(
    title: str,
    grouped: Mapping[str, Sequence[str]],
    category_order: Sequence[str],
) -> str:
    category_blocks: list[str] = []
    for category in category_order:
        events = [event.strip() for event in grouped.get(category, ()) if event.strip()]
        if not events:
            continue
        category_blocks.append(f"**{category}**\n\n" + "\n\n".join(events))
    if not category_blocks:
        return ""
    return f"## {title}\n\n" + "\n\n".join(category_blocks)


def _read_csv(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    if not path.exists():
        raise RedditPublishingError(f"CSV export not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        return [dict(row) for row in reader], fieldnames


def _require_columns(
    path: Path, fieldnames: Sequence[str], required: frozenset[str]
) -> None:
    missing = sorted(required.difference(fieldnames))
    if missing:
        raise RedditPublishingError(
            f"{path.name} is the wrong Notion export; missing columns: "
            + ", ".join(missing)
        )


def _publishing_values(
    path: Path, line_number: int, row: Mapping[str, str]
) -> tuple[str, str, str]:
    category = _required_value(path, line_number, row, "Category")
    if category not in CATEGORY_ORDER:
        raise RedditPublishingError(
            f"{path.name}:{line_number} has unknown Category={category!r}"
        )
    return (
        category,
        _required_value(path, line_number, row, "Event Name"),
        _required_value(path, line_number, row, "Final Post Ready"),
    )


def _required_value(
    path: Path, line_number: int, row: Mapping[str, str], column: str
) -> str:
    value = (row.get(column) or "").strip()
    if not value:
        raise RedditPublishingError(
            f"{path.name}:{line_number} is missing {column!r}"
        )
    return value


def _is_empty_row(row: Mapping[str, str]) -> bool:
    return not any((value or "").strip() for value in row.values())


def _parse_date(value: str) -> date:
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass
    raise RedditPublishingError(
        f"Unsupported date {value!r}; expected MM/DD/YYYY or YYYY-MM-DD"
    )
