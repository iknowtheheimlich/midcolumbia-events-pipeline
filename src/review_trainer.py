"""Deterministic human-correction artifacts for editorial review items.

Attempt_52_ReviewTrainer

This module records review decisions; it does not invent classifier policy. Corrections
remain explicit data that can be promoted into focused rules and regression cases.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from src.publisher_editorial import EditorialEvent

DEFAULT_REVIEW_TRAINING_PATH = Path("artifacts/review/Review_Training.json")
ALLOWED_ACTIONS = {"CATEGORY", "GEOGRAPHY", "SUPPRESS", "ACCEPT_REVIEW"}


@dataclass(frozen=True)
class ReviewTrainingRecord:
    fingerprint: str
    title: str
    source: str
    source_event_id: str | None
    start_date: str
    start_time: str | None
    venue: str
    city: str
    current_category: str | None
    category_confidence: float | None
    category_reason: str | None
    geographic_scope: str | None
    editorial_reason: str | None
    intelligence: dict[str, dict[str, Any]]
    correction: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_review_training_records(
    events: Iterable[EditorialEvent],
    corrections: dict[str, dict[str, Any]] | None = None,
) -> list[ReviewTrainingRecord]:
    correction_map = corrections or {}
    records = [_record(event, correction_map) for event in events]
    return sorted(records, key=lambda item: (item.start_date, item.title.casefold(), item.fingerprint))


def write_review_training_artifact(
    events: Iterable[EditorialEvent],
    path: Path = DEFAULT_REVIEW_TRAINING_PATH,
    *,
    corrections_path: Path | None = None,
) -> list[ReviewTrainingRecord]:
    corrections = load_corrections(corrections_path) if corrections_path else {}
    records = build_review_training_records(events, corrections)
    payload = {
        "schema_version": 1,
        "record_count": len(records),
        "records": [record.to_dict() for record in records],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return records


def load_corrections(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("corrections", payload if isinstance(payload, list) else [])
    if not isinstance(rows, list):
        raise ValueError("review corrections must be a list or contain a 'corrections' list")

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each review correction must be an object")
        fingerprint = str(row.get("fingerprint") or "").strip()
        action = str(row.get("action") or "").strip().upper()
        if not fingerprint:
            raise ValueError("review correction requires fingerprint")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"unsupported review correction action: {action!r}")
        if fingerprint in result:
            raise ValueError(f"duplicate review correction fingerprint: {fingerprint}")
        copied = dict(row)
        copied["action"] = action
        result[fingerprint] = copied
    return result


def _record(
    event: EditorialEvent,
    corrections: dict[str, dict[str, Any]],
) -> ReviewTrainingRecord:
    fingerprint = review_fingerprint(event)
    return ReviewTrainingRecord(
        fingerprint=fingerprint,
        title=event.title,
        source=event.source,
        source_event_id=event.source_event_id,
        start_date=event.start_date,
        start_time=event.display_start_time,
        venue=event.display_venue,
        city=event.display_city,
        current_category=event.semantic_category,
        category_confidence=event.category_confidence,
        category_reason=event.category_reason,
        geographic_scope=event.geographic_scope,
        editorial_reason=event.editorial_reason,
        intelligence=event.intelligence,
        correction=corrections.get(fingerprint),
    )


def review_fingerprint(event: EditorialEvent) -> str:
    identity = "|".join(
        _clean(value)
        for value in (
            event.source,
            event.source_event_id,
            event.canonical_title or event.title,
            event.start_date,
            event.display_start_time,
            event.venue_id or event.display_venue,
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())
