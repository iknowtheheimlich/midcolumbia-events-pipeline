"""Audit generated harvest data for mojibake repairs and unresolved markers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.text_normalization import mojibake_score, normalize_text


HARVEST_ROOT = Path("generated/harvest")
OUTPUT_PATH = Path("generated/encoding_normalization/report.txt")


def main() -> None:
    repaired: list[str] = []
    unresolved: list[str] = []
    files_scanned = 0
    events_scanned = 0

    for path in sorted(HARVEST_ROOT.glob("*/normalized_events.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            continue
        files_scanned += 1
        events_scanned += len(payload)

        for event_index, event in enumerate(payload):
            for field_path, value in walk_strings(event):
                normalized = normalize_text(value)
                label = f"{path.parent.name}[{event_index}].{field_path}"
                if normalized != value:
                    repaired.append(f"{label}\n  before: {value}\n  after:  {normalized}")
                if mojibake_score(normalized) > 0:
                    unresolved.append(f"{label}\n  value: {normalized}")

    lines = [
        "Attempt_25 Encoding Normalization Audit",
        "=======================================",
        "",
        f"Files scanned: {files_scanned}",
        f"Events scanned: {events_scanned}",
        f"Repairable strings: {len(repaired)}",
        f"Unresolved strings: {len(unresolved)}",
        "",
        "Repairable strings:",
        *(repaired or ["  none"]),
        "",
        "Unresolved strings:",
        *(unresolved or ["  none"]),
        "",
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Files scanned: {files_scanned}")
    print(f"Events scanned: {events_scanned}")
    print(f"Repairable strings: {len(repaired)}")
    print(f"Unresolved strings: {len(unresolved)}")
    print(f"Saved report: {OUTPUT_PATH}")


def walk_strings(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Return dotted paths and string values from nested event data."""
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((prefix or "value", value))
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            found.extend(walk_strings(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]" if prefix else f"[{index}]"
            found.extend(walk_strings(item, child))
    return found


if __name__ == "__main__":
    main()
