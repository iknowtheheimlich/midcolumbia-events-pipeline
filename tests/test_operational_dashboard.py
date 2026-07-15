import json
from pathlib import Path

from src.corpus_health import CorpusHealth
from src.operational_dashboard import build_operational_dashboard, render_operational_dashboard
from src.review_operational_metrics import ReviewOperationalMetrics
from src.review_operations_config import ReviewOperationsConfig
from tools.finalize_weekly_run import finalize_weekly_run


def health(**overrides) -> CorpusHealth:
    values = {
        "total_events": 10,
        "distinct_sources": 3,
        "distinct_categories": 4,
        "distinct_venues": 8,
        "distinct_organizers": 5,
        "missing_venue": 0,
        "missing_date": 0,
        "missing_source": 0,
        "category_distribution": {"Sports": 10},
        "source_distribution": {"Example": 10},
    }
    values.update(overrides)
    return CorpusHealth(**values)


def metrics(**overrides) -> ReviewOperationalMetrics:
    values = {
        "active": 0,
        "new": 0,
        "recurring": 0,
        "stale": 0,
        "resolved": 0,
        "due_soon": 0,
        "overdue": 0,
        "oldest_days": 0,
        "opened": 0,
        "carried": 0,
        "net_change": 0,
        "trend": "flat",
        "stale_share": 0.0,
        "capacity_status": "clear",
        "average_opened": 0.0,
        "average_resolved": 0.0,
        "net_clearance": 0.0,
        "weeks_to_clear": 0.0,
    }
    values.update(overrides)
    return ReviewOperationalMetrics(**values)


def test_healthy_dashboard_has_single_operator_view() -> None:
    dashboard = build_operational_dashboard(
        health(), metrics(), ReviewOperationsConfig(), review_batch_exported=0
    )
    report = render_operational_dashboard(dashboard)
    assert dashboard.status == "healthy"
    assert "Pipeline status: HEALTHY" in report
    assert "CORPUS\n------" in report
    assert "REVIEW QUEUE\n------------" in report
    assert "CAPACITY\n--------" in report


def test_review_exceptions_escalate_to_attention() -> None:
    dashboard = build_operational_dashboard(
        health(missing_venue=2),
        metrics(active=3, stale=1, overdue=1, capacity_status="over_capacity"),
        ReviewOperationsConfig(),
        review_batch_exported=3,
    )
    assert dashboard.status == "attention"
    assert "1 overdue review decision(s)" in dashboard.reasons
    assert "review backlog is over capacity" in dashboard.reasons


def test_data_or_report_failures_escalate_to_degraded() -> None:
    dashboard = build_operational_dashboard(
        health(missing_source=1),
        metrics(),
        ReviewOperationsConfig(),
        review_batch_exported=0,
        report_failures=["tools.report_knowledge_drift"],
    )
    assert dashboard.status == "degraded"
    assert dashboard.report_failures == ("tools.report_knowledge_drift",)
    assert "1 corpus event(s) missing source" in dashboard.reasons


def test_finalizer_writes_dashboard_artifacts(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "event_id": "1",
                    "title": "Example",
                    "category": "Sports",
                    "category_confidence": 0.9,
                    "category_needs_review": False,
                    "start_date": "2026-07-15",
                    "source": "Example Source",
                    "venue": "Example Venue",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = finalize_weekly_run(
        input_path,
        history_path=tmp_path / "history.jsonl",
        review_ledger_path=tmp_path / "reviews.jsonl",
        review_backlog_path=tmp_path / "backlog.json",
        throughput_history_path=tmp_path / "throughput.jsonl",
        snapshots_dir=tmp_path / "snapshots",
        artifacts_dir=tmp_path / "artifacts",
        run_reports=False,
    )
    report_path = Path(result["pipeline_health_report"])
    json_path = Path(result["pipeline_health_json"])
    assert report_path.exists()
    assert json_path.exists()
    assert result["pipeline_health_status"] == "healthy"
    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "healthy"
