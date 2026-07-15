"""Batch export and adjudication workflow for classification reviews."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from src.classification_observability import sort_for_category_review
from src.classification_review_feedback import append_feedback, build_feedback


REVIEW_FIELDS = (
    "event_id",
    "title",
    "category",
    "category_confidence",
    "category_confidence_band",
    "category_reason",
    "venue",
    "organizer",
    "source",
    "corrected_category",
    "reviewer_note",
)


@dataclass(frozen=True)
class ReviewBatchResult:
    exported: int
    skipped_not_reviewable: int
    output_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewImportResult:
    rows_read: int
    accepted: int
    corrected: int
    skipped_blank: int
    duplicates: int
    ledger_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def export_review_batch(events: Iterable[dict[str, Any]], output_path: Path) -> ReviewBatchResult:
    reviewable: list[dict[str, Any]] = []
    skipped = 0
    for event in events:
        if not bool(event.get("category_needs_review")):
            skipped += 1
            continue
        reviewable.append(event)

    rows = [_review_row(event) for event in sort_for_category_review(reviewable)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return ReviewBatchResult(len(rows), skipped, str(output_path))


def import_review_batch(batch_path: Path, ledger_path: Path, *, reviewer: str = "human") -> ReviewImportResult:
    rows_read = accepted = corrected = skipped_blank = duplicates = 0
    with batch_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_headers(reader.fieldnames)
        for row in reader:
            rows_read += 1
            original = _text(row.get("category"))
            chosen = _text(row.get("corrected_category"))
            if not chosen:
                skipped_blank += 1
                continue
            event = _event_from_review_row(row)
            feedback = build_feedback(event, chosen, reviewer=reviewer)
            if not append_feedback(ledger_path, feedback):
                duplicates += 1
                continue
            if chosen == original:
                accepted += 1
            else:
                corrected += 1
    return ReviewImportResult(rows_read, accepted, corrected, skipped_blank, duplicates, str(ledger_path))


def load_events(path: Path) -> list[dict[str, Any]]:
    if path.suffix.casefold() == ".jsonl":
        rows = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected object at {path}:{line_number}")
            rows.append(value)
        return rows
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("events", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError(f"Unsupported event payload in {path}")


def _review_row(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": _text(event.get("event_id") or event.get("dedupe_key") or event.get("legacy_dedupe_key")) or "",
        "title": _text(event.get("title")) or "",
        "category": _text(event.get("category")) or "",
        "category_confidence": float(event.get("category_confidence") or 0.0),
        "category_confidence_band": _text(event.get("category_confidence_band")) or "",
        "category_reason": _text(event.get("category_reason")) or "",
        "venue": _text(event.get("canonical_venue") or event.get("venue_registry_name") or event.get("venue")) or "",
        "organizer": _text(event.get("canonical_organizer") or event.get("organizer_registry_name") or event.get("organization") or event.get("organizer") or event.get("host")) or "",
        "source": _text(event.get("source")) or "",
        "corrected_category": "",
        "reviewer_note": "",
    }


def _event_from_review_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "event_id": row.get("event_id"),
        "title": row.get("title"),
        "category": row.get("category"),
        "category_confidence": _float(row.get("category_confidence")),
        "category_reason": row.get("category_reason"),
        "category_evidence": [],
        "venue": row.get("venue"),
        "organizer": row.get("organizer"),
        "source": row.get("source"),
        "reviewer_note": row.get("reviewer_note"),
    }


def _validate_headers(fieldnames: list[str] | None) -> None:
    present = set(fieldnames or [])
    required = {"title", "category", "corrected_category"}
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"Review batch missing required columns: {', '.join(missing)}")


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
