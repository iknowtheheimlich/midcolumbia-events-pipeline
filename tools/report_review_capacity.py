"""Report review capacity from throughput history and current backlog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.operational_defaults import CAPACITY_LOOKBACK_RUNS
from src.review_backlog_aging import load_backlog
from src.review_capacity_planning import analyze_review_capacity, render_capacity_report


def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--throughput-history", type=Path, default=Path("history/review_backlog_throughput.jsonl"))
    parser.add_argument("--backlog", type=Path, default=Path("history/review_backlog.json"))
    parser.add_argument("--lookback", type=int, default=CAPACITY_LOOKBACK_RUNS)
    parser.add_argument("--report", type=Path, default=Path("artifacts/review_capacity_report.txt"))
    args = parser.parse_args()

    plan = analyze_review_capacity(
        load_history(args.throughput_history),
        active_backlog=len(load_backlog(args.backlog)),
        lookback=max(1, args.lookback),
    )
    report = render_capacity_report(plan)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Report path: {args.report}")


if __name__ == "__main__":
    main()
