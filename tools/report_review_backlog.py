"""Update and report unresolved classification review backlog aging."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.classification_review_batch import load_events
from src.review_backlog_aging import load_backlog, reconcile_backlog, render_backlog_report, write_backlog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Classified JSON or JSONL event artifact")
    parser.add_argument("--state", type=Path, default=Path("history/review_backlog.json"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/review_backlog_report.txt"))
    parser.add_argument("--stale-after", type=int, default=3)
    args = parser.parse_args()

    backlog, stats = reconcile_backlog(
        load_events(args.input),
        load_backlog(args.state),
        stale_after=max(2, args.stale_after),
    )
    write_backlog(args.state, backlog)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = render_backlog_report(backlog, stats)
    args.report.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"State path: {args.state}")
    print(f"Report path: {args.report}")


if __name__ == "__main__":
    main()
