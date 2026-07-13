"""Render Reddit markdown from display-ready editorial events and programs.

Attempt_31_RedditRendererCutover
Attempt_33_PublishingContract
Attempt_34_NotionPresentationLayer
Attempt_35_DualPublisher
Attempt_41_ProgramIntelligence

The renderer contains presentation only. Venue cleanup, time grammar, URL choice,
geographic policy, content screening, category routing, and deduplication belong
upstream.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Sequence, TypeAlias

from src.program_intelligence import EditorialProgram, ProgramOccurrence
from src.publisher_editorial import EditorialEvent

Renderable: TypeAlias = EditorialEvent | EditorialProgram

DEFAULT_FOOTNOTE = (
    "This is not an all inclusive list. Events were extracted from allevents.in, "
    "visittri-cities.com, tricityvibe.com."
)


def render_reddit_post(
    events: Iterable[Renderable],
    *,
    footnote: str = DEFAULT_FOOTNOTE,
    category_order: Sequence[str] | None = None,
) -> str:
    """Return old-editor Reddit markdown for publishable events or programs."""
    publishable = [
        event for event in events if event.publication_disposition == "AUTO_PUBLISH"
    ]
    ordered = sorted(publishable, key=_sort_key)

    grouped: dict[str, list[Renderable]] = defaultdict(list)
    for event in ordered:
        grouped[event.start_date].append(event)

    lines: list[str] = []
    for start_date, day_events in grouped.items():
        lines.append(_date_heading(start_date))
        lines.append("")
        if category_order is None:
            lines.extend(render_item_line(event) for event in day_events)
        else:
            lines.extend(_render_category_sections(day_events, category_order))
        lines.append("")

    if footnote.strip():
        lines.append(footnote.strip())

    return "\n".join(lines).rstrip() + "\n"


def render_item_line(event: Renderable) -> str:
    if isinstance(event, EditorialProgram):
        return render_program_line(event)
    return render_event_line(event)


def render_event_line(event: EditorialEvent) -> str:
    """Render one event using the established Reddit markdown line contract."""
    location = _render_location(event)
    parts = [event.title, location]
    if event.display_time:
        parts.append(event.display_time)
    return " | ".join(parts)


def render_program_line(program: EditorialProgram) -> str:
    """Render one program, compressing repeated venue or time dimensions."""
    if len(program.occurrences) == 1:
        occurrence = program.occurrences[0]
        location = _render_occurrence_location(occurrence)
        parts = [program.title, location]
        if occurrence.display_time:
            parts.append(occurrence.display_time)
        return " | ".join(parts)

    venue_keys = {
        (occurrence.display_venue.casefold(), occurrence.display_city.casefold())
        for occurrence in program.occurrences
    }
    if len(venue_keys) == 1:
        occurrence = program.occurrences[0]
        location = _render_occurrence_location(occurrence)
        time_chain = " • ".join(
            occurrence.display_time or "time TBD" for occurrence in program.occurrences
        )
        return f"{program.title} | {location} | {time_chain}"

    occurrence_chain = " • ".join(
        _render_occurrence_summary(occurrence) for occurrence in program.occurrences
    )
    return f"{program.title} | {occurrence_chain}"


def write_reddit_artifact(
    events: Iterable[Renderable],
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
        render_reddit_post(events, footnote=footnote, category_order=category_order),
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def default_artifact_path(week_start: date) -> Path:
    return Path("artifacts") / "reddit" / f"reddit_post_{week_start.isoformat()}.txt"


def default_main_artifact_path() -> Path:
    return Path("artifacts") / "reddit" / "Main_Events_Post.txt"


def default_community_artifact_path() -> Path:
    return Path("artifacts") / "reddit" / "Community_Events_Post.txt"


def _render_category_sections(
    events: Sequence[Renderable],
    category_order: Sequence[str],
) -> list[str]:
    grouped: dict[str, list[Renderable]] = defaultdict(list)
    for event in events:
        if event.semantic_category:
            grouped[event.semantic_category].append(event)

    lines: list[str] = []
    for category in category_order:
        category_events = grouped.get(category, [])
        if not category_events:
            continue
        lines.append(f"## {category}")
        lines.extend(render_item_line(event) for event in category_events)
        lines.append("")
    if lines and not lines[-1]:
        lines.pop()
    return lines


def _sort_key(event: Renderable) -> tuple[str, int, str, str]:
    venue = (
        event.occurrences[0].display_venue
        if isinstance(event, EditorialProgram) and event.occurrences
        else event.display_venue
    )
    return (
        event.start_date,
        _sort_minutes(event.display_start_time),
        event.title.casefold(),
        venue.casefold(),
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


def _render_occurrence_location(occurrence: ProgramOccurrence) -> str:
    value = occurrence.display_venue.strip()
    if value.startswith("[") and "](" in value:
        return value
    venue = _markdown_link(value, occurrence.publication_url)
    return f"{venue}, {occurrence.display_city}" if occurrence.display_city else venue


def _render_occurrence_summary(occurrence: ProgramOccurrence) -> str:
    location = _render_occurrence_location(occurrence)
    return f"{location} {occurrence.display_time}" if occurrence.display_time else location


def _markdown_link(label: str, url: str) -> str:
    clean_label = label.replace("[", "\\[").replace("]", "\\]")
    clean_url = url.replace(" ", "%20").replace(")", "%29")
    return f"[{clean_label}]({clean_url})"
