"""Estimate classification-review capacity from backlog throughput history."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Iterable

from src.operational_defaults import CAPACITY_LOOKBACK_RUNS
from src.plaintext_report import PlaintextReport


@dataclass(frozen=True)
class ReviewCapacityPlan:
    active_backlog: int
    average_opened: float
    average_resolved: float
    net_clearance: float
    weeks_to_clear: float | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_review_capacity(
    history: Iterable[dict[str, Any]],
    *,
    active_backlog: int,
    lookback: int = CAPACITY_LOOKBACK_RUNS,
) -> ReviewCapacityPlan:
    rows = [row for row in history if isinstance(row, dict)][-max(1, lookback):]
    opened = mean(float(row.get("opened", 0)) for row in rows) if rows else 0.0
    resolved = mean(float(row.get("resolved", 0)) for row in rows) if rows else 0.0
    net_clearance = resolved - opened
    weeks_to_clear = active_backlog / net_clearance if active_backlog and net_clearance > 0 else (0.0 if not active_backlog else None)
    status = "clear" if not active_backlog else ("recovering" if net_clearance > 0 else ("balanced" if net_clearance == 0 else "over_capacity"))
    return ReviewCapacityPlan(active_backlog, opened, resolved, net_clearance, weeks_to_clear, status)


def render_capacity_report(plan: ReviewCapacityPlan) -> str:
    eta = "not currently clearing" if plan.weeks_to_clear is None else f"{plan.weeks_to_clear:.1f} weeks"
    return (
        PlaintextReport("Attempt 90 Review Capacity Planning")
        .lines(
            (
                f"Active backlog: {plan.active_backlog}",
                f"Average opened/week: {plan.average_opened:.1f}",
                f"Average resolved/week: {plan.average_resolved:.1f}",
                f"Net clearance/week: {plan.net_clearance:+.1f}",
                f"Estimated time to clear: {eta}",
                f"Status: {plan.status}",
            )
        )
        .render()
    )
