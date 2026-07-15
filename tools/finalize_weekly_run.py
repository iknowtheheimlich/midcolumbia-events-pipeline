"""Finalize a successful weekly run by updating history and operational reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from src.classified_history import load_jsonl, merge_classified_history, write_jsonl
from src.classification_review_batch import export_review_batch
from src.classification_review_feedback import load_feedback
from src.corpus_health import analyze_corpus_health, render_corpus_health
from src.corpus_snapshots import create_corpus_snapshot
from tools.update_classified_history import load_events


def finalize_weekly_run(
    input_path: Path,
    *,
    history_path: Path = Path("history/classified_events.jsonl"),
    review_ledger_path: Path = Path("history/classification_reviews.jsonl"),
    snapshots_dir: Path = Path("history/snapshots"),
    artifacts_dir: Path = Path("artifacts"),
    run_reports: bool = True,
) -> dict:
    incoming_events = load_events(input_path)
    existing = load_jsonl(history_path)
    merged, stats = merge_classified_history(existing, incoming_events)
    snapshot_path = create_corpus_snapshot(history_path, snapshots_dir=snapshots_dir)
    write_jsonl(history_path, merged)

    health = analyze_corpus_health(merged)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "corpus_health.json").write_text(
        json.dumps(health.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (artifacts_dir / "corpus_health_report.txt").write_text(
        render_corpus_health(health), encoding="utf-8"
    )

    review_batch_path = artifacts_dir / "classification_review_batch.csv"
    review_batch = export_review_batch(
        incoming_events,
        review_batch_path,
        reviewed_feedback=load_feedback(review_ledger_path),
    )

    report_failures: list[str] = []
    if run_reports:
        commands = (
            [sys.executable, "-m", "tools.report_venue_intelligence", str(history_path)],
            [sys.executable, "-m", "tools.report_knowledge_drift", str(history_path)],
            [sys.executable, "-m", "tools.report_classification_reviews"],
            [sys.executable, "-m", "tools.report_confidence_calibration"],
        )
        for command in commands:
            result = subprocess.run(command, check=False)
            if result.returncode:
                report_failures.append(" ".join(command[2:]))

    return {
        **stats,
        "history_path": str(history_path),
        "snapshot_path": str(snapshot_path) if snapshot_path else None,
        "health_report": str(artifacts_dir / "corpus_health_report.txt"),
        "review_batch_path": str(review_batch_path),
        "review_batch_exported": review_batch.exported,
        "review_batch_skipped_reviewed": review_batch.skipped_already_reviewed,
        "report_failures": report_failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Final classified JSON or JSONL artifact")
    parser.add_argument("--history", type=Path, default=Path("history/classified_events.jsonl"))
    parser.add_argument("--review-ledger", type=Path, default=Path("history/classification_reviews.jsonl"))
    parser.add_argument("--snapshots-dir", type=Path, default=Path("history/snapshots"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--skip-reports", action="store_true")
    args = parser.parse_args()

    result = finalize_weekly_run(
        args.input,
        history_path=args.history,
        review_ledger_path=args.review_ledger,
        snapshots_dir=args.snapshots_dir,
        artifacts_dir=args.artifacts_dir,
        run_reports=not args.skip_reports,
    )
    print("Attempt 85 Weekly Finalization")
    print("==============================")
    print(f"Incoming classified: {result['incoming']}")
    print(f"Inserted: {result['inserted']}")
    print(f"Updated: {result['updated']}")
    print(f"Skipped unclassified: {result['skipped_unclassified']}")
    print(f"Corpus total: {result['total']}")
    print(f"History path: {result['history_path']}")
    print(f"Snapshot path: {result['snapshot_path'] or 'None (empty initial corpus)'}")
    print(f"Health report: {result['health_report']}")
    print(
        f"Review batch: {result['review_batch_path']} "
        f"({result['review_batch_exported']} events; "
        f"{result['review_batch_skipped_reviewed']} already reviewed)"
    )
    if result["report_failures"]:
        print("Non-blocking report failures: " + ", ".join(result["report_failures"]))


if __name__ == "__main__":
    main()
