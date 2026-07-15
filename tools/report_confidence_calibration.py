"""Report how classifier confidence compares with human review outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.classification_review_feedback import load_feedback
from src.confidence_calibration import analyze_calibration, render_calibration_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ledger",
        nargs="?",
        type=Path,
        default=Path("history/classification_reviews.jsonl"),
    )
    parser.add_argument("--min-reviews", type=int, default=10)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary = analyze_calibration(load_feedback(args.ledger), min_reviews=args.min_reviews)
    report = render_calibration_report(summary)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
