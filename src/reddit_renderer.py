"""Render Reddit markdown from display-ready editorial events.

Attempt_31_RedditRendererCutover
Attempt_33_PublishingContract
Attempt_34_NotionPresentationLayer
Attempt_35_DualPublisher

The renderer contains presentation only. Venue cleanup, time grammar, URL choice,
geographic policy, content screening, category routing, and deduplication belong
upstream.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Sequence

from src.publisher_editorial import EditorialEvent


DEFAULT_FOOTNOTE = (
    "This is not an all inclusive list. Events were extracted from allevents.in, "
    "visittri-cities.com, tricityvibe.com."
)


def render_reddit_post(
    events: Iterable[EditorialEvent],
    *,
    footnote: str = DEFAULT_FOOTNOTE,
    category_order: Sequence[str] | None = None,
) -> str:
    """Return old-editor Reddit markdown for auto-publish editorial events.

    ``category_order`` is additive. When omitted, the legacy date-only layout is
    preserved. Dual production publishers pass the publishing profile order and
    receive category sections within each date.
    """
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
        if category_order is None:
            lines.extend(render_event_line(event) for event in day_events)
        else:
            lines.extend(_render_category_sections(day_events, category_order))
        lines.append("")

    if footnote.strip():
        lines.append(footnote.strip())

    return "\n".join(lines).rstrip() + "\n"


def render_event_line(event: EditorialEvent) -> str:
    """Render one event using the established Reddit markdown line contract."""
    location = _render_location(event)
    parts = [event.title, location]
    if event.display_time:
        parts.append(event.display_time)
    return " | ".join(parts)


def write_reddit_artifact(
    events: Iterable[EditorialEvent],
    output_path: Path,
    *,
    footnote: str = DEFAULT_FOOTNOTE,
    category_order: Sequence[str] | None = None,
) -> Path:
    """Write a generated Reddit post outside fixture directories."""
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated Reddit artifacts must remain separate from fixtures")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_reddit_post(
            events,
            footnote=footnote,
            category_order=category_order,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def default_artifact_path(week_start: date) -> Path:
    """Return the legacy repository-relative production artifact path."""
    return Path("artifacts") / "reddit" / f"reddit_post_{week_start.isoformat()}.txt"


def default_main_artifact_path() -> Path:
    return Path("artifacts") / "reddit" / "Main_Events_Post.txt"


def default_community_artifact_path() -> Path:
    return Path("artifacts") / "reddit" / "Community_Events_Post.txt"


def _render_category_sections(
    events: Sequence[EditorialEvent],
    category_order: Sequence[str],
) -> list[str]:
    grouped: dict[str, list[EditorialEvent]] = defaultdict(list)
    for event in events:
        if event.semantic_category:
            grouped[event.semantic_category].append(event)

    lines: list[str] = []
    for category in category_order:
        category_events = grouped.get(category, [])
        if not category_events:
            continue
        lines.append(f"## {category}")
        lines.extend(render_event_line(event) for event in category_events)
        lines.append("")
    if lines and not lines[-1]:
        lines.pop()
    return lines


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
    for format_string in ("%H:%M", "%H:%M:%S", "%I:%M %p"):
        try:
            parsed = datetime.strptime(value.strip(), format_string)
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            continue
    return 24 * 60


def _date_heading(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return f"#{parsed.day:02d} {parsed.strftime('%B')}"


def _render_location(event: EditorialEvent) -> str:
    value = event.display_venue.strip()
    if value.startswith("[") and "](" in value:
        return value
    venue = _markdown_link(value, event.publication_url)
    return f"{venue}, {event.display_city}" if event.display_city else venue


def _markdown_link(label: str, url: str) -> str:
    clean_label = label.replace("[", "\\[").replace("]", "\\]")
    clean_url = url.replace(" ", "%20").replace(")", "%29")
    return f"[{clean_label}]({clean_url})"
