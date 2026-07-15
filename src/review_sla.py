"""Service-level monitoring for unresolved classification review decisions."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any

from src.operational_defaults import (
    SLA_DUE_AFTER_DAYS,
    SLA_OVERDUE_AFTER_APPEARANCES,
    SLA_OVERDUE_AFTER_DAYS,
)


@dataclass(frozen=True)
class ReviewSLAStats:
    active: int
    due_soon: int
    overdue: int
    oldest_days: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def apply_review_sla(
    backlog: dict[str, dict[str, Any]],
    *,
    as_of: str | None = None,
    due_after_days: int = SLA_DUE_AFTER_DAYS,
    overdue_after_days: int = SLA_OVERDUE_AFTER_DAYS,
    overdue_after_appearances: int = SLA_OVERDUE_AFTER_APPEARANCES,
) -> tuple[dict[str, dict[str, Any]], ReviewSLAStats]:
    today = date.fromisoformat(as_of or date.today().isoformat())
    enriched: dict[str, dict[str, Any]] = {}
    due_soon = overdue = oldest_days = 0
    for key, original in backlog.items():
        row = dict(original)
        first_seen = date.fromisoformat(str(row.get("first_seen") or today.isoformat()))
        age_days = max(0, (today - first_seen).days)
        appearances = int(row.get("appearances", 0))
        if age_days >= max(1, overdue_after_days) or appearances >= max(2, overdue_after_appearances):
            sla_status = "overdue"
            overdue += 1
        elif age_days >= max(1, due_after_days):
            sla_status = "due_soon"
            due_soon += 1
        else:
            sla_status = "within_sla"
        row["age_days"] = age_days
        row["sla_status"] = sla_status
        enriched[key] = row
        oldest_days = max(oldest_days, age_days)
    return enriched, ReviewSLAStats(len(enriched), due_soon, overdue, oldest_days)


def render_review_sla_report(backlog: dict[str, dict[str, Any]], stats: ReviewSLAStats) -> str:
    lines = [
        "Attempt 89 Review SLA",
        "=====================",
        "",
        f"Active: {stats.active}",
        f"Due soon: {stats.due_soon}",
        f"Overdue: {stats.overdue}",
        f"Oldest age: {stats.oldest_days} days",
        "",
        "OVERDUE / DUE SOON",
        "------------------",
    ]
    rows = [row for row in backlog.values() if row.get("sla_status") != "within_sla"]
    rows.sort(key=lambda row: (0 if row.get("sla_status") == "overdue" else 1, -int(row.get("age_days", 0)), float(row.get("confidence", 0.0))))
    if not rows:
        lines.append("None")
    else:
        for row in rows:
            lines.append(
                f"{row.get('title', '')} | {row.get('category', '')} | "
                f"{row.get('sla_status')} | age={row.get('age_days', 0)}d | appearances={row.get('appearances', 0)}"
            )
    return "\n".join(lines).rstrip() + "\n"
