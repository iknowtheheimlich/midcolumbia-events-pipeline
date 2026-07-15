from __future__ import annotations

import argparse
from pathlib import Path

from src.classification_review_batch import export_review_batch, load_events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/classification_review_batch.csv"))
    args = parser.parse_args()
    result = export_review_batch(load_events(args.input), args.output)
    print("Attempt 83 Classification Review Batch Export")
    print("=============================================")
    print(f"Exported: {result.exported}")
    print(f"Skipped not reviewable: {result.skipped_not_reviewable}")
    print(f"Output: {result.output_path}")


if __name__ == "__main__":
    main()
