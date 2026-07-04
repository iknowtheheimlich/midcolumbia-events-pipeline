"""Inspect captured Richland Library raw fixture shape.

Usage:
    python -m tools.inspect_richland_library_fixture
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("fixtures/richland_library/raw_events.json")


def main() -> None:
    payload = json.loads(DEFAULT_INPUT.read_text(encoding="utf-8"))
    print(f"Top-level type: {type(payload).__name__}")

    if isinstance(payload, list):
        print(f"List length: {len(payload)}")
        if payload:
            print_sample(payload[0])
        return

    if isinstance(payload, dict):
        print("Top-level keys:")
        for key in payload.keys():
            print(f"- {key}")
        sample = first_eventish_value(payload)
        if sample is not None:
            print("\nFirst event-like sample:")
            print_sample(sample)


def first_eventish_value(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, dict):
        for child in value.values():
            found = first_eventish_value(child)
            if found is not None:
                return found
    return None


def print_sample(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, (str, int, float, bool)) or child is None:
                print(f"{key}: {child}")
            else:
                print(f"{key}: {type(child).__name__}")
    else:
        print(value)


if __name__ == "__main__":
    main()
