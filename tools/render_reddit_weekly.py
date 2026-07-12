"""Generate a weekly Reddit post from fully enriched pipeline event JSON.

The input must be the deduplicated production event queue, not a raw adapter export.
Generated posts are written under artifacts/reddit by default and never into fixtures.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Any

from src.publisher_editorial import (
    auto_publish_events,
    prepare_editorial_events,
    rejected_events,
    review_events,
)
from src.publisher_projection import project_events
from src.reddit_renderer import default_artifact_path, write_reddit_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Deduplicated enriched event JSON")
    parser.add_argument(
        "--week-start",
        type=_parse_date,
        required=True,
        help="First included date in YYYY-MM-DD format",
    )
    parser.add_argument("--days", type=int, default=7, help="Number of included days")
    parser.add_argument("--output", type=Path, help="Output .txt path")
    args = parser.parse_args()

    if args.days < 1:
        parser.error("--days must be at least 1")

    events = _load_events(args.input)
    weekly_events = _filter_week(events, args.week_start, args.days)
    editorial = prepare_editorial_events(project_events(weekly_events))
    publishable = auto_publish_events(editorial)
    review = review_events(editorial)
    rejected = rejected_events(editorial)

    output = args.output or default_artifact_path(args.week_start)
    write_reddit_artifact(publishable, output)

    print(f"Input events: {len(events)}")
    print(f"Weekly events: {len(weekly_events)}")
    print(f"Auto-published: {len(publishable)}")
    print(f"Review queue: {len(review)}")
    print(f"Rejected: {len(rejected)}")
    print(f"Artifact: {output}")
    return 0


def _load_events(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("deduplicated_publisher_ready_events", "events"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                payload = candidate
                break
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("input must contain a JSON list of event objects")
    return payload


def _filter_week(
    events: list[dict[str, Any]],
    week_start: date,
    days: int,
) -> list[dict[str, Any]]:
    week_end = week_start + timedelta(days=days)
    selected: list[dict[str, Any]] = []
    for event in events:
        value = event.get("start_date")
        try:
            event_date = _parse_date(str(value))
        except ValueError:
            continue
        if week_start <= event_date < week_end:
            selected.append(event)
    return selected


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


if __name__ == "__main__":
    raise SystemExit(main())
