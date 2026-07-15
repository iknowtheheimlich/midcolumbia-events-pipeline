import json
from pathlib import Path

import pytest

from src.review_backlog_aging import BacklogStats
from src.review_backlog_throughput import BacklogThroughput
from src.review_capacity_planning import ReviewCapacityPlan
from src.review_operational_metrics import consolidate_review_metrics
from src.review_sla import ReviewSLAStats
from tools.finalize_weekly_run import finalize_weekly_run


def components(active: int = 2):
    backlog = BacklogStats(active=active, new=1 if active else 0, recurring=0, stale=max(0, active - 1), resolved=3)
    sla = ReviewSLAStats(active=active, due_soon=1 if active else 0, overdue=max(0, active - 1), oldest_days=12 if active else 0)
    throughput = BacklogThroughput(
        prior_active=3,
        current_active=active,
        opened=1,
        carried=1 if active else 0,
        resolved=2,
        net_change=active - 3,
        stale=max(0, active - 1),
        stale_share=((active - 1) / active) if active else 0.0,
        trend="shrinking" if active < 3 else "flat",
    )
    capacity = ReviewCapacityPlan(
        active_backlog=active,
        average_opened=1.0,
        average_resolved=2.0,
        net_clearance=1.0,
        weeks_to_clear=float(active),
        status="recovering" if active else "clear",
    )
    return backlog, sla, throughput, capacity


def test_consolidates_existing_metrics_without_recalculation() -> None:
    metrics = consolidate_review_metrics(*components())
    assert metrics.active == 2
    assert metrics.stale == 1
    assert metrics.overdue == 1
    assert metrics.net_change == -1
    assert metrics.capacity_status == "recovering"
    assert metrics.weeks_to_clear == 2.0


def test_serializes_flat_operational_snapshot() -> None:
    metrics = consolidate_review_metrics(*components())
    payload = metrics.to_dict()
    assert payload["average_resolved"] == 2.0
    assert payload["trend"] == "shrinking"
    assert set(payload) == {
        "active", "new", "recurring", "stale", "resolved", "due_soon", "overdue",
        "oldest_days", "opened", "carried", "net_change", "trend", "stale_share",
        "capacity_status", "average_opened", "average_resolved", "net_clearance", "weeks_to_clear",
    }


def test_rejects_disagreeing_active_counts() -> None:
    backlog, sla, throughput, capacity = components()
    mismatched_sla = ReviewSLAStats(active=3, due_soon=1, overdue=1, oldest_days=12)
    with pytest.raises(ValueError, match="disagree on active backlog"):
        consolidate_review_metrics(backlog, mismatched_sla, throughput, capacity)


def test_finalizer_writes_consolidated_metrics_artifact(tmp_path: Path) -> None:
    event = {
        "event_id": "1",
        "title": "Example",
        "category": "Sports",
        "category_confidence": 0.4,
        "category_confidence_band": "low",
        "category_reason": "description_rule=sports",
        "category_needs_review": True,
    }
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps([event]), encoding="utf-8")
    result = finalize_weekly_run(
        input_path,
        history_path=tmp_path / "classified.jsonl",
        review_ledger_path=tmp_path / "reviews.jsonl",
        review_backlog_path=tmp_path / "backlog.json",
        throughput_history_path=tmp_path / "throughput.jsonl",
        snapshots_dir=tmp_path / "snapshots",
        artifacts_dir=tmp_path / "artifacts",
        run_reports=False,
    )
    metrics_path = Path(result["review_operational_metrics"])
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert payload == result["review_metrics"]
    assert payload["active"] == result["review_backlog_active"] == 1
    assert payload["capacity_status"] == result["review_capacity_status"]
