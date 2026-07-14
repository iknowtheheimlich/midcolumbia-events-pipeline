"""Human-readable report of recovered price and labeled schedule details."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from src.supplemental_details import enrich_event_supplemental_details

DEFAULT_SUPPLEMENTAL_DETAIL_PATH = Path("artifacts") / "reddit" / "Supplemental_Details.txt"


def build_supplemental_detail_rows(
    events: Iterable[dict[str, Any]],
    *,
    week_start: date,
    days: int = 7,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    week_end = week_start + timedelta(days=days)
    for event in events:
        start_date = str(event.get("start_date") or "")
        if not (week_start.isoformat() <= start_date < week_end.isoformat()):
            continue
        enriched = enrich_event_supplemental_details(event)
        cost = enriched.get("cost")
        schedule_items = enriched.get("schedule_items") or []
        if not cost and not schedule_items:
            continue
        rows.append(
            {
                "title": str(enriched.get("title") or "Untitled event"),
                "start_date": start_date,
                "venue": str(enriched.get("venue") or ""),
                "source": str(enriched.get("source") or ""),
                "url": str(enriched.get("external_url") or enriched.get("url") or ""),
                "cost": cost,
                "cost_source": enriched.get("cost_source"),
                "schedule_items": schedule_items,
                "schedule_source": enriched.get("schedule_source"),
            }
        )
    return sorted(rows, key=lambda row: (row["start_date"], row["title"].casefold()))


def render_supplemental_detail_audit(rows: Iterable[dict[str, Any]]) -> str:
    values = list(rows)
    lines = [
        "Supplemental Detail Recovery",
        "============================",
        "",
        f"Events with recovered details: {len(values)}",
        "",
    ]
    for row in values:
        lines.append(f"{row['start_date']} | {row['title']}")
        location = row.get("venue") or "Venue unavailable"
        source = row.get("source") or "Unknown source"
        lines.append(f"  {location} | {source}")
        if row.get("cost"):
            lines.append(f"  Cost: {row['cost']} ({row.get('cost_source') or 'source'})")
        for item in row.get("schedule_items") or []:
            lines.append(f"  Schedule: {item['time']} — {item['label']}")
        if row.get("url"):
            lines.append(f"  URL: {row['url']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_supplemental_detail_audit(
    events: Iterable[dict[str, Any]],
    output_path: Path = DEFAULT_SUPPLEMENTAL_DETAIL_PATH,
    *,
    week_start: date,
    days: int = 7,
) -> Path:
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated supplemental detail audit must remain separate from fixtures")
    rows = build_supplemental_detail_rows(events, week_start=week_start, days=days)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_supplemental_detail_audit(rows), encoding="utf-8", newline="\n")
    return output_path
