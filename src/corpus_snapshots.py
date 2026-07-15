"""Snapshot and restore support for the classified event history corpus."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import shutil


def corpus_checksum(path: Path) -> str:
    """Return the SHA-256 checksum of a corpus file, or the empty-file checksum."""
    data = path.read_bytes() if path.exists() else b""
    return sha256(data).hexdigest()


def create_corpus_snapshot(
    history_path: Path,
    *,
    snapshots_dir: Path = Path("history/snapshots"),
    timestamp: datetime | None = None,
) -> Path | None:
    """Copy the current corpus to a timestamped snapshot before mutation.

    Empty or missing history does not produce a snapshot because there is nothing to
    restore. Snapshot names include a checksum prefix, making identical states easy to
    recognize without opening the file.
    """
    if not history_path.exists() or history_path.stat().st_size == 0:
        return None
    moment = timestamp or datetime.now(timezone.utc)
    stamp = moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checksum = corpus_checksum(history_path)[:12]
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    target = snapshots_dir / f"classified_events_{stamp}_{checksum}.jsonl"
    shutil.copy2(history_path, target)
    return target


def restore_corpus_snapshot(snapshot_path: Path, history_path: Path) -> None:
    """Restore one JSONL snapshot to the active corpus path."""
    if not snapshot_path.exists():
        raise FileNotFoundError(snapshot_path)
    if snapshot_path.suffix.casefold() != ".jsonl":
        raise ValueError("Corpus snapshots must be JSONL files")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot_path, history_path)
