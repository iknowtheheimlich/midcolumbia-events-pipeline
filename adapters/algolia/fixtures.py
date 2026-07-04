"""Fixture helpers for Algolia-backed adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_fixture(path: str | Path) -> dict[str, Any] | list[Any]:
    """Load a JSON fixture."""
    fixture_path = Path(path)
    with fixture_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json_fixture(path: str | Path, payload: dict[str, Any] | list[Any]) -> None:
    """Save a JSON fixture with deterministic formatting."""
    fixture_path = Path(path)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    with fixture_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
