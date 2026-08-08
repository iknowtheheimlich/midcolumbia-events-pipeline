from __future__ import annotations

import json
from pathlib import Path

from tests.history_helpers import finalizer_paths
from tools.finalize_weekly_run import finalize_weekly_run


def test_finalizer_exports_review_batch(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    source.write_text(
        json.dumps(
            [
                {
                    "event_id": "1",
                    "title": "Needs Review",
                    "category": "Community Events",
                    "category_confidence": 0.4,
                    "category_confidence_band": "low",
                    "category_reason": "description_rule=test",
                    "category_needs_review": True,
                },
                {
                    "event_id": "2",
                    "title": "No Review",
                    "category": "Sports",
                    "category_confidence": 0.95,
                    "category_confidence_band": "high",
                    "category_reason": "title_rule=sports",
                    "category_needs_review": False,
                },
            ]
        ),
        encoding="utf-8",
    )
    paths = finalizer_paths(tmp_path)
    artifacts = paths["artifacts_dir"]
    result = finalize_weekly_run(
        source,
        **finalizer_paths(tmp_path),
        run_reports=False,
    )
    assert result["review_batch_exported"] == 1
    batch = artifacts / "classification_review_batch.csv"
    assert batch.exists()
    text = batch.read_text(encoding="utf-8")
    assert "Needs Review" in text
    assert "No Review" not in text


def test_finalizer_returns_review_batch_path_when_empty(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    source.write_text("[]", encoding="utf-8")
    paths = finalizer_paths(tmp_path)
    result = finalize_weekly_run(
        source,
        **finalizer_paths(tmp_path),
        run_reports=False,
    )
    assert result["review_batch_exported"] == 0
    assert Path(result["review_batch_path"]).exists()
