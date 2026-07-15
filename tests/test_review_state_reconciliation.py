from __future__ import annotations

import csv
from pathlib import Path

from src.classification_review_batch import export_review_batch


def _event(category: str = "Community Programs") -> dict:
    return {
        "event_id": "event-1",
        "title": "Example",
        "category": category,
        "category_confidence": 0.4,
        "category_confidence_band": "low",
        "category_reason": "description_rule=test",
        "category_needs_review": True,
    }


def test_reviewed_decision_is_suppressed(tmp_path: Path) -> None:
    output = tmp_path / "batch.csv"
    result = export_review_batch(
        [_event()],
        output,
        reviewed_feedback=[{"event_id": "event-1", "original_category": "Community Programs"}],
    )
    assert result.exported == 0
    assert result.skipped_already_reviewed == 1


def test_changed_decision_returns_to_review(tmp_path: Path) -> None:
    output = tmp_path / "batch.csv"
    result = export_review_batch(
        [_event("Classes/Workshops")],
        output,
        reviewed_feedback=[{"event_id": "event-1", "original_category": "Community Programs"}],
    )
    assert result.exported == 1
    assert result.skipped_already_reviewed == 0
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["category"] == "Classes/Workshops"


def test_different_event_is_not_suppressed(tmp_path: Path) -> None:
    output = tmp_path / "batch.csv"
    result = export_review_batch(
        [_event()],
        output,
        reviewed_feedback=[{"event_id": "event-2", "original_category": "Community Programs"}],
    )
    assert result.exported == 1
