"""File and finalizer helpers for tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def finalizer_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "history_path": tmp_path / "classified.jsonl",
        "review_ledger_path": tmp_path / "reviews.jsonl",
        "review_backlog_path": tmp_path / "backlog.json",
        "throughput_history_path": tmp_path / "throughput.jsonl",
        "snapshots_dir": tmp_path / "snapshots",
        "artifacts_dir": tmp_path / "artifacts",
    }
