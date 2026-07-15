"""Canonical loading for JSON and JSONL event artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EVENT_LIST_KEYS = (
    "events",
    "all_events",
    "publisher_ready_events",
    "deduplicated_publisher_ready_events",
    "items",
    "records",
)


def load_event_records(path: Path) -> list[dict[str, Any]]:
    """Load event objects from JSONL, a top-level JSON list, or a known envelope."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.casefold() == ".jsonl":
        return _load_jsonl(path, text)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc.msg}") from exc

    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in EVENT_LIST_KEYS:
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    raise ValueError(f"No event list found in {path}")


def _load_jsonl(path: Path, text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL in {path} at line {line_number}: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Expected object at {path}:{line_number}")
        rows.append(value)
    return rows
