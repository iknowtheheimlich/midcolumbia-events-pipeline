"""Summarize classification review corrections without changing classifier rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.classification_review_feedback import analyze_feedback, load_feedback, render_feedback_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=Path("history/classification_reviews.jsonl"))
    parser.add_argument("--json-output", type=Path, default=Path("artifacts/classification_review_summary.json"))
    parser.add_argument("--report-output", type=Path, default=Path("artifacts/classification_review_report.txt"))
    args = parser.parse_args()

    summary = analyze_feedback(load_feedback(args.ledger))
    report = render_feedback_report(summary)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    args.report_output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
