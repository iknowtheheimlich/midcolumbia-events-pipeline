"""Shared adapter fixture helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | Path, payload: Any) -> None:
    fixture_path = Path(path)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def save_text(path: str | Path, payload: str) -> None:
    fixture_path = Path(path)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(payload, encoding="utf-8")