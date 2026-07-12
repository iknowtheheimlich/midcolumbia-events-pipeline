"""Render Reddit markdown from display-ready editorial events.

Attempt_31_RedditRendererCutover
Attempt_33_PublishingContract

The renderer contains presentation only. Venue cleanup, time grammar, URL choice,
geographic policy, content screening, category routing, and deduplication belong
upstream.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from src.publisher_editorial import EditorialEvent


DEFAULT_FOOTNOTE = (
    "This is not an all inclusive list. Events were extracted from allevents.in, "
    "visittri-cities.com, tricityvibe.com."
)


def render_reddit_post(
    events: Iterable[EditorialEvent],
    *,
    footnote: str = DEFAULT_FOOTNOTE,
) -> str:
    """Return old-editor Reddit markdown for auto-publish editorial events."""
    publishable = [
        event for event in events if event.publication_disposition == "AUTO_PUBLISH"
    ]
    ordered = sorted(publishable, key=_sort_key)

    grouped: dict[str, list[EditorialEvent]] = defaultdict(list)
    for event in ordered:
        grouped[event.start_date].append(event)

    lines: list[str] = []
    for start_date, day_events in grouped.items():
        lines.append(_date_heading(start_date))
        lines.append("")
        lines.extend(render_event_line(event) for event in day_events)
        lines.append("")

    if footnote.strip():
        lines.append(footnote.strip())

    return "\n".join(lines).rstrip() + "\n"


def render_event_line(event: EditorialEvent) -> str:
    """Render one event using the established Reddit markdown line contract."""
    venue = _markdown_link(event.display_venue, event.publication_url)
    location = f"{venue}, {event.display_city}" if event.display_city else venue
    parts = [event.title, location]
    if event.display_time:
        parts.append(event.display_time)
    return " | ".join(parts)


def write_reddit_artifact(
    events: Iterable[EditorialEvent],
    output_path: Path,
    *,
    footnote: str = DEFAULT_FOOTNOTE,
) -> Path:
    """Write a generated Reddit post outside fixture directories."""
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated Reddit artifacts must remain separate from fixtures")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_reddit_post(events, footnote=footnote),
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def default_artifact_path(week_start: date) -> Path:
    """Return the repository-relative production artifact path for one week."""
    return Path("artifacts") / "reddit" / f"reddit_post_{week_start.isoformat()}.txt"


def _sort_key(event: EditorialEvent) -> tuple[str, int, str, str]:
    return (
        event.start_date,
        _sort_minutes(event.display_start_time),
        event.title.casefold(),
        event.display_venue.casefold(),
    )


def _sort_minutes(value: str | None) -> int:
    if not value:
        return 24 * 60 + 1
    for format_string in ("%H:%M", "%I:%M %p"):
        try:
            parsed = datetime.strptime(value.strip(), format_string)
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            continue
    return 24 * 60


def _date_heading(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return f"#{parsed.day:02d} {parsed.strftime('%B')}"


def _markdown_link(label: str, url: str) -> str:
    clean_label = label.replace("[", "\\[").replace("]", "\\]")
    clean_url = url.replace(" ", "%20").replace(")", "%29")
    return f"[{clean_label}]({clean_url})"
