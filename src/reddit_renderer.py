"""Render Reddit markdown from display-ready editorial events and programs."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
import re
from typing import Iterable, Sequence, TypeAlias

from src.program_intelligence import EditorialProgram, ProgramOccurrence
from src.publisher_editorial import EditorialEvent
from src.publishing_contract import PublishingProfile
from src.url_canonicalizer import validate_public_http_url

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
    publishable = [event for event in events if event.publication_disposition == "AUTO_PUBLISH"]
    ordered = sorted(publishable, key=_sort_key)
    active_category_order = tuple(category_order or PublishingProfile.load().category_order)
    grouped: dict[str, list[Renderable]] = defaultdict(list)
    for event in ordered:
        grouped[event.start_date].append(event)
    lines: list[str] = []
    for start_date, day_events in grouped.items():
        lines.append(_date_heading(start_date))
        lines.append("")
        lines.extend(_render_category_sections(day_events, active_category_order))
        lines.append("")
    if footnote.strip():
        lines.append(footnote.strip())
    return "\n".join(lines).rstrip() + "\n"


def render_item_line(event: Renderable) -> str:
    return render_program_line(event) if isinstance(event, EditorialProgram) else render_event_line(event)


def render_event_line(event: EditorialEvent) -> str:
    parts = [_render_title(event.title), _render_location(event)]
    if event.display_time:
        parts.append(event.display_time)
    parts.extend(_render_credit_parts(event))
    return " | ".join(parts)


def render_program_line(program: EditorialProgram) -> str:
    if len(program.occurrences) == 1:
        occurrence = program.occurrences[0]
        parts = [_render_title(program.title), _render_occurrence_location(occurrence)]
        if occurrence.display_time:
            parts.append(occurrence.display_time)
        parts.extend(_render_credit_parts(occurrence))
        return " | ".join(parts)

    venue_keys = {
        (occurrence.display_venue.casefold(), occurrence.display_city.casefold())
        for occurrence in program.occurrences
    }
    if len(venue_keys) == 1:
        occurrence = program.occurrences[0]
        time_chain = " • ".join(item.display_time or "time TBD" for item in program.occurrences)
        parts = [_render_title(program.title), _render_occurrence_location(occurrence), time_chain]
        parts.extend(_shared_credit_parts(program.occurrences))
        return " | ".join(parts)

    occurrence_chain = " • ".join(_render_occurrence_summary(item) for item in program.occurrences)
    parts = [_render_title(program.title), occurrence_chain]
    parts.extend(_shared_credit_parts(program.occurrences))
    return " | ".join(parts)


def write_reddit_artifact(
    events: Iterable[Renderable],
    output_path: Path,
    *,
    footnote: str = DEFAULT_FOOTNOTE,
    category_order: Sequence[str] | None = None,
) -> Path:
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


def _render_category_sections(events: Sequence[Renderable], category_order: Sequence[str]) -> list[str]:
    grouped: dict[str, list[Renderable]] = defaultdict(list)
    for event in events:
        category = event.semantic_category or getattr(event, "category", None)
        if category:
            grouped[category].append(event)

    configured_categories = list(dict.fromkeys(category_order))
    configured_category_set = set(configured_categories)
    unexpected_categories = sorted(
        category
        for category in grouped
        if category not in configured_category_set
    )

    lines: list[str] = []
    for category in (*configured_categories, *unexpected_categories):
        category_events = grouped.get(category, [])
        if not category_events:
            continue
        if lines:
            lines.append("")
        lines.extend((f"## {category}", ""))
        for index, event in enumerate(category_events):
            if index:
                lines.append("")
            lines.append(render_item_line(event))
    return lines


def _sort_key(event: Renderable) -> tuple[str, int, str, str]:
    venue = event.occurrences[0].display_venue if isinstance(event, EditorialProgram) and event.occurrences else event.display_venue
    return event.start_date, _sort_minutes(event.display_start_time), event.title.casefold(), venue.casefold()


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
    value = _plain_venue_label(event.display_venue)
    venue = _markdown_link(value, event.publication_url)
    return f"{venue}, {event.display_city}" if event.display_city else venue


def _render_occurrence_location(occurrence: ProgramOccurrence) -> str:
    value = _plain_venue_label(occurrence.display_venue)
    venue = _markdown_link(value, occurrence.publication_url)
    return f"{venue}, {occurrence.display_city}" if occurrence.display_city else venue


def _plain_venue_label(value: str) -> str:
    text = value.strip()
    match = re.fullmatch(r"\[([^\]]+)\]\([^)]+\)(?:\s*,\s*.*)?", text)
    return match.group(1).strip() if match else text


def _render_occurrence_summary(occurrence: ProgramOccurrence) -> str:
    location = _render_occurrence_location(occurrence)
    return f"{location} {occurrence.display_time}" if occurrence.display_time else location


def _render_credit_parts(value: object) -> list[str]:
    parts: list[str] = []
    organization = getattr(value, "display_organization", None)
    organization_url = getattr(value, "display_organization_url", None)
    artist = getattr(value, "display_artist", None)
    artist_url = getattr(value, "display_artist_url", None)
    if organization:
        label = _markdown_link(organization, organization_url) if organization_url else organization
        parts.append(f"Host: {label}")
    if artist:
        label = _markdown_link(artist, artist_url) if artist_url else artist
        parts.append(f"Artist: {label}")
    return parts


def _shared_credit_parts(occurrences: Sequence[ProgramOccurrence]) -> list[str]:
    if not occurrences:
        return []
    first = _render_credit_parts(occurrences[0])
    return first if all(_render_credit_parts(item) == first for item in occurrences[1:]) else []


def _markdown_link(label: str, url: str) -> str:
    if not label.strip():
        raise ValueError("Markdown link label is empty")
    validate_public_http_url(url, field=f"Markdown destination for {label!r}")
    clean_label = label.replace("[", "\\[").replace("]", "\\]")
    clean_url = url.replace(" ", "%20").replace(")", "%29")
    return f"[{clean_label}]({clean_url})"


def _render_title(value: str) -> str:
    """Escape field separators while preserving the visible title punctuation."""
    return value.replace("|", "\\|")
