"""Measure weekly classification-review backlog flow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from src.plaintext_report import PlaintextReport


@dataclass(frozen=True)
class BacklogThroughput:
    prior_active: int
    current_active: int
    opened: int
    carried: int
    resolved: int
    net_change: int
    stale: int
    stale_share: float
    trend: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_backlog_throughput(
    prior: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> BacklogThroughput:
    prior_keys = set(prior)
    current_keys = set(current)
    opened = len(current_keys - prior_keys)
    carried = len(current_keys & prior_keys)
    resolved = len(prior_keys - current_keys)
    current_active = len(current_keys)
    net_change = current_active - len(prior_keys)
    stale = sum(1 for row in current.values() if row.get("status") == "stale")
    stale_share = stale / current_active if current_active else 0.0
    trend = "shrinking" if net_change < 0 else ("growing" if net_change > 0 else "flat")
    return BacklogThroughput(
        prior_active=len(prior_keys),
        current_active=current_active,
        opened=opened,
        carried=carried,
        resolved=resolved,
        net_change=net_change,
        stale=stale,
        stale_share=stale_share,
        trend=trend,
    )


def append_throughput(path: Path, run_date: str, metrics: BacklogThroughput) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"run_date": run_date, **metrics.to_dict()}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def render_throughput_report(metrics: BacklogThroughput) -> str:
    return (
        PlaintextReport("Attempt 88 Review Backlog Throughput")
        .lines(
            (
                f"Prior active: {metrics.prior_active}",
                f"Current active: {metrics.current_active}",
                f"Opened: {metrics.opened}",
                f"Carried: {metrics.carried}",
                f"Resolved: {metrics.resolved}",
                f"Net change: {metrics.net_change:+d}",
                f"Stale: {metrics.stale} ({metrics.stale_share:.1%})",
                f"Trend: {metrics.trend}",
            )
        )
        .render()
    )
