"""Unified operator view assembled from existing weekly pipeline metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from src.corpus_health import CorpusHealth
from src.plaintext_report import PlaintextReport
from src.review_operational_metrics import ReviewOperationalMetrics
from src.review_operations_config import ReviewOperationsConfig


@dataclass(frozen=True)
class OperationalDashboard:
    status: str
    reasons: tuple[str, ...]
    corpus: dict[str, Any]
    review: dict[str, Any]
    configuration: dict[str, int]
    review_batch_exported: int
    report_failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_operational_dashboard(
    health: CorpusHealth,
    metrics: ReviewOperationalMetrics,
    config: ReviewOperationsConfig,
    *,
    review_batch_exported: int,
    report_failures: Iterable[str] = (),
) -> OperationalDashboard:
    failures = tuple(report_failures)
    degraded: list[str] = []
    attention: list[str] = []

    if failures:
        degraded.append(f"{len(failures)} analytical report failure(s)")
    if health.missing_source:
        degraded.append(f"{health.missing_source} corpus event(s) missing source")
    if health.missing_date:
        degraded.append(f"{health.missing_date} corpus event(s) missing date")

    if metrics.overdue:
        attention.append(f"{metrics.overdue} overdue review decision(s)")
    if metrics.stale:
        attention.append(f"{metrics.stale} stale review decision(s)")
    if metrics.capacity_status == "over_capacity":
        attention.append("review backlog is over capacity")
    if health.missing_venue:
        attention.append(f"{health.missing_venue} corpus event(s) missing venue")

    reasons = tuple(degraded or attention or ["no operational exceptions detected"])
    status = "degraded" if degraded else ("attention" if attention else "healthy")
    return OperationalDashboard(
        status=status,
        reasons=reasons,
        corpus=health.to_dict(),
        review=metrics.to_dict(),
        configuration=config.to_dict(),
        review_batch_exported=review_batch_exported,
        report_failures=failures,
    )


def render_operational_dashboard(dashboard: OperationalDashboard) -> str:
    corpus = dashboard.corpus
    review = dashboard.review
    eta = review.get("weeks_to_clear")
    eta_text = "not currently clearing" if eta is None else f"{float(eta):.1f} weeks"

    report = PlaintextReport("Attempt 98 Weekly Pipeline Health")
    report.line(f"Pipeline status: {dashboard.status.upper()}")
    report.section("STATUS REASONS").lines(dashboard.reasons)
    report.section("CORPUS").lines(
        (
            f"Events: {corpus['total_events']}",
            f"Sources: {corpus['distinct_sources']}",
            f"Categories: {corpus['distinct_categories']}",
            f"Venues: {corpus['distinct_venues']}",
            f"Organizers: {corpus['distinct_organizers']}",
            f"Missing venue/date/source: {corpus['missing_venue']}/{corpus['missing_date']}/{corpus['missing_source']}",
        )
    )
    report.section("REVIEW QUEUE").lines(
        (
            f"Active: {review['active']}",
            f"New / recurring / stale: {review['new']} / {review['recurring']} / {review['stale']}",
            f"Due soon / overdue: {review['due_soon']} / {review['overdue']}",
            f"Oldest unresolved: {review['oldest_days']} days",
            f"Trend: {review['trend']} ({review['net_change']:+d})",
            f"Batch exported: {dashboard.review_batch_exported}",
        )
    )
    report.section("CAPACITY").lines(
        (
            f"Status: {review['capacity_status']}",
            f"Average opened/week: {review['average_opened']:.1f}",
            f"Average resolved/week: {review['average_resolved']:.1f}",
            f"Net clearance/week: {review['net_clearance']:+.1f}",
            f"Estimated time to clear: {eta_text}",
        )
    )
    report.section("CONFIGURATION").lines(
        f"{name}: {value}" for name, value in dashboard.configuration.items()
    )
    report.section("ANALYTICAL REPORTS").lines(dashboard.report_failures or ("All completed",))
    return report.render()
