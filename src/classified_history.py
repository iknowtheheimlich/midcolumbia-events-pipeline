"""Persistent, deduplicated corpus of final classified events.

Attempt_77_ClassifiedHistoryCorpus

The corpus is JSONL, deterministic, and append-safe through upsert semantics. Only
final classified events are retained. Raw collection artifacts do not belong here.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

_HISTORY_FIELDS = (
    "event_id",
    "source",
    "url",
    "title",
    "start_date",
    "end_date",
    "start_time",
    "end_time",
    "category",
    "category_confidence",
    "category_reason",
    "venue",
    "venue_registry_name",
    "canonical_venue",
    "venue_type",
    "registry_venue_type",
    "organization",
    "organizer",
    "host",
    "presented_by",
    "organizer_registry_name",
    "canonical_organizer",
    "city",
)


def stable_event_id(event: dict[str, Any]) -> str:
    """Return a stable identity suitable for repeated weekly corpus upserts."""
    explicit = _text(event.get("event_id") or event.get("legacy_dedupe_key") or event.get("dedupe_key"))
    if explicit:
        return explicit
    source = _text(event.get("source")) or "unknown"
    url = _text(event.get("url"))
    if url:
        return f"{source.casefold()}|{url}"
    identity = "|".join(
        (
            source.casefold(),
            (_text(event.get("title")) or "").casefold(),
            _text(event.get("start_date") or event.get("date") or event.get("event_date")) or "",
            (_text(event.get("venue_registry_name") or event.get("canonical_venue") or event.get("venue")) or "").casefold(),
        )
    )
    return "derived|" + sha256(identity.encode("utf-8")).hexdigest()[:24]


def project_classified_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Project one final classified event into the durable history contract."""
    category = _text(event.get("category"))
    if not category:
        return None
    projected = {field: event.get(field) for field in _HISTORY_FIELDS if event.get(field) is not None}
    projected["event_id"] = stable_event_id(event)
    projected["category"] = category
    return projected


def merge_classified_history(
    existing: Iterable[dict[str, Any]],
    incoming: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Upsert classified events and return deterministic corpus plus statistics."""
    indexed: dict[str, dict[str, Any]] = {}
    for row in existing:
        projected = project_classified_event(row)
        if projected:
            indexed[projected["event_id"]] = projected
    before = len(indexed)
    eligible = 0
    inserted = 0
    updated = 0
    skipped = 0
    for event in incoming:
        projected = project_classified_event(event)
        if projected is None:
            skipped += 1
            continue
        eligible += 1
        event_id = projected["event_id"]
        prior = indexed.get(event_id)
        if prior is None:
            inserted += 1
        elif prior != projected:
            updated += 1
        indexed[event_id] = projected
    rows = sorted(
        indexed.values(),
        key=lambda row: (
            _text(row.get("start_date")) or "",
            (_text(row.get("title")) or "").casefold(),
            row["event_id"],
        ),
    )
    return rows, {
        "existing": before,
        "incoming": eligible,
        "inserted": inserted,
        "updated": updated,
        "skipped_unclassified": skipped,
        "total": len(rows),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Expected object at {path}:{line_number}")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
