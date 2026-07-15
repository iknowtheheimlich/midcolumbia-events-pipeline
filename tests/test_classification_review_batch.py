from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.classification_review_batch import export_review_batch, import_review_batch
from src.classification_review_feedback import load_feedback


def test_export_includes_only_reviewable_events_and_sorts_lowest_first(tmp_path: Path) -> None:
    output = tmp_path / "batch.csv"
    events = [
        {"event_id": "b", "title": "Medium", "category": "Events/Hangouts", "category_confidence": 0.70, "category_confidence_band": "low", "category_reason": "description_rule=x", "category_needs_review": True},
        {"event_id": "a", "title": "Low", "category": "Community Programs", "category_confidence": 0.30, "category_confidence_band": "low", "category_reason": "no_category_rule_matched", "category_needs_review": True},
        {"event_id": "c", "title": "High", "category": "Sports", "category_confidence": 0.99, "category_needs_review": False},
    ]
    result = export_review_batch(events, output)
    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert result.exported == 2
    assert result.skipped_not_reviewable == 1
    assert [row["event_id"] for row in rows] == ["a", "b"]


def test_import_records_acceptance_correction_and_blank(tmp_path: Path) -> None:
    batch = tmp_path / "batch.csv"
    ledger = tmp_path / "reviews.jsonl"
    with batch.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "title", "category", "category_confidence", "category_reason", "venue", "organizer", "source", "corrected_category"])
        writer.writeheader()
        writer.writerow({"event_id": "1", "title": "One", "category": "Sports", "category_confidence": "0.8", "corrected_category": "Sports"})
        writer.writerow({"event_id": "2", "title": "Two", "category": "Sports", "category_confidence": "0.6", "corrected_category": "Community Programs"})
        writer.writerow({"event_id": "3", "title": "Three", "category": "Sports", "category_confidence": "0.4", "corrected_category": ""})
    result = import_review_batch(batch, ledger, reviewer="Dina")
    assert result.rows_read == 3
    assert result.accepted == 1
    assert result.corrected == 1
    assert result.skipped_blank == 1
    assert len(load_feedback(ledger)) == 2


def test_import_is_idempotent_for_same_batch(tmp_path: Path) -> None:
    batch = tmp_path / "batch.csv"
    ledger = tmp_path / "reviews.jsonl"
    with batch.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "title", "category", "corrected_category"])
        writer.writeheader()
        writer.writerow({"event_id": "1", "title": "One", "category": "Sports", "corrected_category": "Sports"})
    first = import_review_batch(batch, ledger)
    second = import_review_batch(batch, ledger)
    assert first.accepted == 1
    assert second.duplicates == 1
    assert len(load_feedback(ledger)) == 1


def test_import_requires_correction_column(tmp_path: Path) -> None:
    batch = tmp_path / "bad.csv"
    ledger = tmp_path / "reviews.jsonl"
    batch.write_text("title,category\nOne,Sports\n", encoding="utf-8")
    with pytest.raises(ValueError, match="corrected_category"):
        import_review_batch(batch, ledger)
