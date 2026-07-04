"""Inspect legacy CSV headers and sample rows.

Usage:
    python -m tools.inspect_legacy_csv --input "D:\\Carls_Instructions\\Mission_Control\\Reddit\\Instructions\\output\\unified_events.csv"
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect legacy CSV columns")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=3)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        print("Headers:")
        for field in reader.fieldnames or []:
            print(f"- {field}")

        print("\nSample rows:")
        for index, row in enumerate(reader):
            if index >= args.rows:
                break
            print(f"\nRow {index + 1}:")
            for key, value in row.items():
                if value not in (None, ""):
                    print(f"{key}: {value}")


if __name__ == "__main__":
    main()
