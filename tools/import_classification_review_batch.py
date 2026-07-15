from __future__ import annotations

import argparse
from pathlib import Path

from src.classification_review_batch import import_review_batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("--ledger", type=Path, default=Path("history/classification_reviews.jsonl"))
    parser.add_argument("--reviewer", default="human")
    args = parser.parse_args()
    result = import_review_batch(args.batch, args.ledger, reviewer=args.reviewer)
    print("Attempt 83 Classification Review Batch Import")
    print("=============================================")
    print(f"Rows read: {result.rows_read}")
    print(f"Accepted: {result.accepted}")
    print(f"Corrected: {result.corrected}")
    print(f"Skipped blank: {result.skipped_blank}")
    print(f"Duplicates: {result.duplicates}")
    print(f"Ledger: {result.ledger_path}")


if __name__ == "__main__":
    main()
