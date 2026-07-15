from pathlib import Path

from src.classified_history import (
    load_jsonl,
    merge_classified_history,
    project_classified_event,
    stable_event_id,
    write_jsonl,
)


def test_unclassified_event_is_not_projected():
    assert project_classified_event({"title": "Mystery"}) is None


def test_legacy_dedupe_key_is_preferred_for_identity():
    event = {"legacy_dedupe_key": "source|123", "title": "Example", "category": "Sports"}
    assert stable_event_id(event) == "source|123"


def test_source_and_url_produce_stable_identity():
    event = {"source": "AllEvents", "url": "https://example.test/1", "category": "Sports"}
    assert stable_event_id(event) == "allevents|https://example.test/1"


def test_fallback_identity_is_deterministic():
    event = {"source": "Library", "title": "Story Time", "start_date": "2026-07-01", "venue": "Library", "category": "Community Programs"}
    assert stable_event_id(event) == stable_event_id(dict(event))
    assert stable_event_id(event).startswith("derived|")


def test_merge_inserts_updates_and_skips_unclassified():
    existing = [{"event_id": "x", "title": "Old", "category": "Sports", "start_date": "2026-07-01"}]
    incoming = [
        {"event_id": "x", "title": "Corrected", "category": "Sports", "start_date": "2026-07-01"},
        {"event_id": "y", "title": "New", "category": "Music/Comedy", "start_date": "2026-07-02"},
        {"event_id": "z", "title": "Unclassified"},
    ]
    rows, stats = merge_classified_history(existing, incoming)
    assert [row["event_id"] for row in rows] == ["x", "y"]
    assert rows[0]["title"] == "Corrected"
    assert stats == {
        "existing": 1,
        "incoming": 2,
        "inserted": 1,
        "updated": 1,
        "skipped_unclassified": 1,
        "total": 2,
    }


def test_repeated_run_is_idempotent():
    event = {"event_id": "x", "title": "Same", "category": "Sports", "start_date": "2026-07-01"}
    first, _ = merge_classified_history([], [event])
    second, stats = merge_classified_history(first, [event])
    assert second == first
    assert stats["inserted"] == 0
    assert stats["updated"] == 0
    assert stats["total"] == 1


def test_jsonl_round_trip(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    rows = [{"event_id": "x", "title": "Café", "category": "Food & Drink"}]
    write_jsonl(path, rows)
    assert load_jsonl(path) == rows
