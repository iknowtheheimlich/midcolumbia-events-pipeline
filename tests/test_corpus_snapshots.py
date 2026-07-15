from datetime import datetime, timezone
from pathlib import Path

from src.corpus_snapshots import corpus_checksum, create_corpus_snapshot, restore_corpus_snapshot


def test_empty_history_does_not_create_snapshot(tmp_path: Path):
    history = tmp_path / "classified_events.jsonl"
    assert create_corpus_snapshot(history, snapshots_dir=tmp_path / "snapshots") is None


def test_snapshot_name_contains_timestamp_and_checksum(tmp_path: Path):
    history = tmp_path / "classified_events.jsonl"
    history.write_text('{"event_id":"1","category":"Sports"}\n', encoding="utf-8")
    snapshot = create_corpus_snapshot(
        history,
        snapshots_dir=tmp_path / "snapshots",
        timestamp=datetime(2026, 7, 15, 12, 30, tzinfo=timezone.utc),
    )
    assert snapshot is not None
    assert snapshot.name.startswith("classified_events_20260715T123000Z_")
    assert snapshot.read_text(encoding="utf-8") == history.read_text(encoding="utf-8")


def test_restore_replaces_active_corpus(tmp_path: Path):
    snapshot = tmp_path / "snapshot.jsonl"
    history = tmp_path / "history.jsonl"
    snapshot.write_text('{"event_id":"old","category":"Sports"}\n', encoding="utf-8")
    history.write_text('{"event_id":"bad","category":"Other"}\n', encoding="utf-8")
    restore_corpus_snapshot(snapshot, history)
    assert history.read_text(encoding="utf-8") == snapshot.read_text(encoding="utf-8")
    assert corpus_checksum(history) == corpus_checksum(snapshot)


def test_restore_rejects_non_jsonl(tmp_path: Path):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("[]", encoding="utf-8")
    try:
        restore_corpus_snapshot(snapshot, tmp_path / "history.jsonl")
    except ValueError as exc:
        assert "JSONL" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
