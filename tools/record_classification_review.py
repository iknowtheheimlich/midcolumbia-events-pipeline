"""Record one human classification review in the append-only feedback ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.classification_review_feedback import append_feedback, build_feedback


def load_event(path: Path, event_id: str | None) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and not any(isinstance(payload.get(key), list) for key in ("events", "all_events", "publisher_ready_events", "deduplicated_publisher_ready_events")):
        return payload
    rows = payload if isinstance(payload, list) else next(
        (payload[key] for key in ("events", "all_events", "publisher_ready_events", "deduplicated_publisher_ready_events") if isinstance(payload.get(key), list)),
        [],
    )
    if event_id is None:
        if len(rows) != 1:
            raise ValueError("--event-id is required when input contains multiple events")
        return rows[0]
    for row in rows:
        if isinstance(row, dict) and str(row.get("event_id") or row.get("dedupe_key") or row.get("legacy_dedupe_key")) == event_id:
            return row
    raise ValueError(f"Event not found: {event_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON event or event collection")
    parser.add_argument("corrected_category")
    parser.add_argument("--event-id")
    parser.add_argument("--reviewer", default="human")
    parser.add_argument("--ledger", type=Path, default=Path("history/classification_reviews.jsonl"))
    args = parser.parse_args()

    feedback = build_feedback(
        load_event(args.input, args.event_id),
        args.corrected_category,
        reviewer=args.reviewer,
    )
    inserted = append_feedback(args.ledger, feedback)
    print("Attempt 81 Classification Review Feedback")
    print("============================================")
    print(f"Recorded: {'yes' if inserted else 'no (duplicate)'}")
    print(f"Event ID: {feedback.event_id}")
    print(f"Original category: {feedback.original_category or 'None'}")
    print(f"Corrected category: {feedback.corrected_category}")
    print(f"Ledger: {args.ledger}")


if __name__ == "__main__":
    main()
