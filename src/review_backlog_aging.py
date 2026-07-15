"""Persistent aging for unresolved classification review decisions."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

from src.operational_defaults import STALE_AFTER_APPEARANCES


@dataclass(frozen=True)
class BacklogStats:
    active: int
    new: int
    recurring: int
    stale: int
    resolved: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def decision_key(event: dict[str, Any]) -> str:
    event_id = str(event.get("event_id") or event.get("dedupe_key") or event.get("legacy_dedupe_key") or "").strip()
    category = str(event.get("category") or "").strip()
    return f"{event_id}|{category}"


def load_backlog(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def reconcile_backlog(
    events: Iterable[dict[str, Any]],
    prior: dict[str, dict[str, Any]],
    *,
    seen_on: str | None = None,
    stale_after: int = STALE_AFTER_APPEARANCES,
) -> tuple[dict[str, dict[str, Any]], BacklogStats]:
    today = seen_on or date.today().isoformat()
    current: dict[str, dict[str, Any]] = {}
    new = recurring = stale = 0
    for event in events:
        if not bool(event.get("category_needs_review")):
            continue
        key = decision_key(event)
        if key == "|":
            continue
        previous = prior.get(key)
        appearances = int(previous.get("appearances", 0)) + 1 if previous else 1
        row = {
            "event_id": str(event.get("event_id") or event.get("dedupe_key") or event.get("legacy_dedupe_key") or ""),
            "title": str(event.get("title") or ""),
            "category": str(event.get("category") or ""),
            "confidence": float(event.get("category_confidence") or 0.0),
            "first_seen": previous.get("first_seen", today) if previous else today,
            "last_seen": today,
            "appearances": appearances,
            "status": "stale" if appearances >= stale_after else ("recurring" if appearances > 1 else "new"),
        }
        current[key] = row
        if row["status"] == "new":
            new += 1
        elif row["status"] == "recurring":
            recurring += 1
        else:
            stale += 1
    resolved = len(set(prior) - set(current))
    return current, BacklogStats(len(current), new, recurring, stale, resolved)


def write_backlog(path: Path, backlog: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(backlog.items(), key=lambda item: (-int(item[1].get("appearances", 0)), float(item[1].get("confidence", 0.0)), item[0])))
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_backlog_report(backlog: dict[str, dict[str, Any]], stats: BacklogStats) -> str:
    lines = [
        "Attempt 86 Review Backlog Aging",
        "================================",
        "",
        f"Active: {stats.active}",
        f"New: {stats.new}",
        f"Recurring: {stats.recurring}",
        f"Stale: {stats.stale}",
        f"Resolved since prior run: {stats.resolved}",
        "",
        "STALE / RECURRING",
        "-----------------",
    ]
    rows = [row for row in backlog.values() if row.get("status") != "new"]
    if not rows:
        lines.append("None")
    else:
        for row in rows:
            lines.append(f"{row['title']} | {row['category']} | {row['confidence']:.2f} | {row['status']} | appearances={row['appearances']}")
    return "\n".join(lines).rstrip() + "\n"
