"""Finalize a successful weekly run by updating history and operational reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from src.classified_history import load_jsonl, merge_classified_history, write_jsonl
from src.corpus_health import analyze_corpus_health, render_corpus_health
from tools.update_classified_history import load_events


def finalize_weekly_run(
    input_path: Path,
    *,
    history_path: Path = Path("history/classified_events.jsonl"),
    artifacts_dir: Path = Path("artifacts"),
    run_reports: bool = True,
) -> dict:
    existing = load_jsonl(history_path)
    merged, stats = merge_classified_history(existing, load_events(input_path))
    write_jsonl(history_path, merged)

    health = analyze_corpus_health(merged)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "corpus_health.json").write_text(
        json.dumps(health.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (artifacts_dir / "corpus_health_report.txt").write_text(
        render_corpus_health(health), encoding="utf-8"
    )

    report_failures: list[str] = []
    if run_reports:
        commands = (
            [sys.executable, "-m", "tools.report_venue_intelligence", str(history_path)],
            [sys.executable, "-m", "tools.report_knowledge_drift", str(history_path)],
        )
        for command in commands:
            result = subprocess.run(command, check=False)
            if result.returncode:
                report_failures.append(" ".join(command[2:]))

    return {
        **stats,
        "history_path": str(history_path),
        "health_report": str(artifacts_dir / "corpus_health_report.txt"),
        "report_failures": report_failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Final classified JSON or JSONL artifact")
    parser.add_argument("--history", type=Path, default=Path("history/classified_events.jsonl"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--skip-reports", action="store_true")
    args = parser.parse_args()

    result = finalize_weekly_run(
        args.input,
        history_path=args.history,
        artifacts_dir=args.artifacts_dir,
        run_reports=not args.skip_reports,
    )
    print("Attempt 78 Weekly Finalization")
    print("==============================")
    print(f"Incoming classified: {result['incoming']}")
    print(f"Inserted: {result['inserted']}")
    print(f"Updated: {result['updated']}")
    print(f"Skipped unclassified: {result['skipped_unclassified']}")
    print(f"Corpus total: {result['total']}")
    print(f"History path: {result['history_path']}")
    print(f"Health report: {result['health_report']}")
    if result["report_failures"]:
        print("Non-blocking report failures: " + ", ".join(result["report_failures"]))


if __name__ == "__main__":
    main()
