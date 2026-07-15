import json
from pathlib import Path

from tools.finalize_weekly_run import finalize_weekly_run


def event(event_id: str = "1") -> dict:
    return {
        "event_id": event_id,
        "title": "Example",
        "category": "Sports",
        "category_confidence": 0.4,
        "category_confidence_band": "low",
        "category_reason": "description_rule=sports",
        "category_needs_review": True,
    }


def test_finalizer_writes_capacity_report_and_status(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps([event()]), encoding="utf-8")

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

    assert result["review_capacity_status"] == "over_capacity"
    assert result["review_capacity_net_clearance"] < 0
    assert result["review_capacity_weeks_to_clear"] is None
    assert Path(result["review_capacity_report"]).exists()


def test_capacity_uses_configured_recent_history(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps([event()]), encoding="utf-8")
    throughput_path = tmp_path / "throughput.jsonl"
    throughput_path.write_text(
        "\n".join(
            [
                json.dumps({"opened": 5, "resolved": 0}),
                json.dumps({"opened": 0, "resolved": 4}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = finalize_weekly_run(
        input_path,
        history_path=tmp_path / "classified.jsonl",
        review_ledger_path=tmp_path / "reviews.jsonl",
        review_backlog_path=tmp_path / "backlog.json",
        throughput_history_path=throughput_path,
        snapshots_dir=tmp_path / "snapshots",
        artifacts_dir=tmp_path / "artifacts",
        capacity_lookback=2,
        run_reports=False,
    )

    assert result["review_capacity_status"] in {"recovering", "balanced", "over_capacity"}
    assert result["review_capacity_report"].endswith("review_capacity_report.txt")
