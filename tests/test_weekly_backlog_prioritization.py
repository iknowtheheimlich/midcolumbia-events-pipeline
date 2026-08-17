import csv
import json
from pathlib import Path

from src.classification_review_batch import export_review_batch
from tests.history_helpers import finalizer_paths
from tools.finalize_weekly_run import finalize_weekly_run


def event(event_id: str, title: str, confidence: float = 0.4) -> dict:
    return {
        "event_id": event_id,
        "title": title,
        "category": "Sports",
        "category_confidence": confidence,
        "category_confidence_band": "low",
        "category_reason": "description_rule=sports",
        "category_needs_review": True,
    }


def test_stale_decisions_sort_before_new_even_with_higher_confidence(tmp_path: Path) -> None:
    output = tmp_path / "batch.csv"
    events = [event("new", "New", 0.20), event("stale", "Stale", 0.60)]
    backlog = {
        "new|Sports": {"status": "new", "appearances": 1, "first_seen": "2026-07-15"},
        "stale|Sports": {"status": "stale", "appearances": 4, "first_seen": "2026-07-01"},
    }
    export_review_batch(events, output, backlog=backlog)
    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert [row["event_id"] for row in rows] == ["stale", "new"]
    assert rows[0]["review_status"] == "stale"
    assert rows[0]["appearances"] == "4"


def test_missing_backlog_metadata_defaults_to_new(tmp_path: Path) -> None:
    output = tmp_path / "batch.csv"
    export_review_batch([event("1", "One")], output)
    row = next(csv.DictReader(output.open(encoding="utf-8")))
    assert row["review_status"] == "new"
    assert row["appearances"] == "1"


def test_finalizer_writes_backlog_state_and_report(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps([event("1", "One")]), encoding="utf-8")
    result = finalize_weekly_run(
        input_path,
        **finalizer_paths(tmp_path),
        run_reports=False,
    )
    assert result["review_backlog_active"] == 1
    assert Path(result["review_backlog_path"]).exists()
    assert Path(result["review_backlog_report"]).exists()
    batch_rows = list(csv.DictReader(Path(result["review_batch_path"]).open(encoding="utf-8")))
    assert batch_rows[0]["review_status"] == "new"
