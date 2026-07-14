"""Weekly event completeness report for editorial and source-quality review."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from src.event_completeness import score_event_completeness, summarize_completeness

DEFAULT_COMPLETENESS_AUDIT_PATH = Path("artifacts") / "reddit" / "Completeness_Audit.txt"


def build_completeness_rows(
    events: Iterable[dict[str, Any]],
    *,
    week_start: date,
    days: int = 7,
    threshold: int = 80,
) -> list[dict[str, Any]]:
    week_end = week_start + timedelta(days=days)
    rows: list[dict[str, Any]] = []
    for event in events:
        start_date = str(event.get("start_date") or "")
        if not (week_start.isoformat() <= start_date < week_end.isoformat()):
            continue
        details = score_event_completeness(event)
        if details["percent"] >= threshold:
            continue
        rows.append(
            {
                "title": str(event.get("title") or "Untitled event"),
                "start_date": start_date,
                "source": str(event.get("source") or "Unknown source"),
                "venue": str(event.get("venue") or ""),
                "url": str(event.get("external_url") or event.get("url") or ""),
                **details,
            }
        )
    return sorted(rows, key=lambda row: (row["percent"], row["start_date"], row["title"].casefold()))


def render_completeness_audit(
    events: Iterable[dict[str, Any]],
    *,
    week_start: date,
    days: int = 7,
    threshold: int = 80,
) -> str:
    weekly = [
        event
        for event in events
        if week_start.isoformat() <= str(event.get("start_date") or "") < (week_start + timedelta(days=days)).isoformat()
    ]
    summary = summarize_completeness(weekly)
    rows = build_completeness_rows(weekly, week_start=week_start, days=days, threshold=threshold)
    lines = [
        "Event Completeness Audit",
        "========================",
        "",
        f"Weekly events measured: {summary['event_count']}",
        f"Average completeness: {summary['average_percent']}%",
        f"Events below {threshold}%: {len(rows)}",
        "",
        "Most commonly missing fields:",
    ]
    for field, count in list(summary["missing_counts"].items())[:10]:
        lines.append(f"  {field}: {count}")
    if rows:
        lines.extend(["", "Low-completeness events:"])
        for row in rows:
            lines.append(f"{row['percent']}% | {row['start_date']} | {row['title']}")
            lines.append(f"  {row['venue'] or 'Venue unavailable'} | {row['source']}")
            lines.append(f"  Missing: {', '.join(row['missing_fields'])}")
            if row["url"]:
                lines.append(f"  URL: {row['url']}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_completeness_audit(
    events: Iterable[dict[str, Any]],
    output_path: Path = DEFAULT_COMPLETENESS_AUDIT_PATH,
    *,
    week_start: date,
    days: int = 7,
    threshold: int = 80,
) -> Path:
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated completeness audit must remain separate from fixtures")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_completeness_audit(events, week_start=week_start, days=days, threshold=threshold),
        encoding="utf-8",
        newline="\n",
    )
    return output_path
