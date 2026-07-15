"""Consolidated operational metrics for classification review workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.review_backlog_aging import BacklogStats
from src.review_backlog_throughput import BacklogThroughput
from src.review_capacity_planning import ReviewCapacityPlan
from src.review_sla import ReviewSLAStats


@dataclass(frozen=True)
class ReviewOperationalMetrics:
    active: int
    new: int
    recurring: int
    stale: int
    resolved: int
    due_soon: int
    overdue: int
    oldest_days: int
    opened: int
    carried: int
    net_change: int
    trend: str
    stale_share: float
    capacity_status: str
    average_opened: float
    average_resolved: float
    net_clearance: float
    weeks_to_clear: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def consolidate_review_metrics(
    backlog: BacklogStats,
    sla: ReviewSLAStats,
    throughput: BacklogThroughput,
    capacity: ReviewCapacityPlan,
) -> ReviewOperationalMetrics:
    """Package already-computed review metrics into one immutable snapshot."""
    if backlog.active != sla.active or backlog.active != throughput.current_active:
        raise ValueError(
            "Review metric inputs disagree on active backlog: "
            f"backlog={backlog.active}, sla={sla.active}, throughput={throughput.current_active}"
        )
    if capacity.active_backlog != backlog.active:
        raise ValueError(
            "Review capacity active backlog does not match backlog metrics: "
            f"capacity={capacity.active_backlog}, backlog={backlog.active}"
        )
    return ReviewOperationalMetrics(
        active=backlog.active,
        new=backlog.new,
        recurring=backlog.recurring,
        stale=backlog.stale,
        resolved=backlog.resolved,
        due_soon=sla.due_soon,
        overdue=sla.overdue,
        oldest_days=sla.oldest_days,
        opened=throughput.opened,
        carried=throughput.carried,
        net_change=throughput.net_change,
        trend=throughput.trend,
        stale_share=throughput.stale_share,
        capacity_status=capacity.status,
        average_opened=capacity.average_opened,
        average_resolved=capacity.average_resolved,
        net_clearance=capacity.net_clearance,
        weeks_to_clear=capacity.weeks_to_clear,
    )
