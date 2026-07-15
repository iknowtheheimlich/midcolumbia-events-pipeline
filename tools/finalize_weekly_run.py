"""Finalize a successful weekly run by updating history and operational reports."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import subprocess
import sys

from src.classified_history import load_jsonl, merge_classified_history, write_jsonl
from src.classification_review_batch import export_review_batch
from src.classification_review_feedback import load_feedback
from src.corpus_health import analyze_corpus_health, render_corpus_health
from src.corpus_snapshots import create_corpus_snapshot
from src.operational_defaults import (
    CAPACITY_LOOKBACK_RUNS,
    SLA_DUE_AFTER_DAYS,
    SLA_OVERDUE_AFTER_APPEARANCES,
    SLA_OVERDUE_AFTER_DAYS,
    STALE_AFTER_APPEARANCES,
)
from src.review_backlog_aging import load_backlog, reconcile_backlog, render_backlog_report, write_backlog
from src.review_backlog_throughput import analyze_backlog_throughput, append_throughput, render_throughput_report
from src.review_capacity_planning import analyze_review_capacity, render_capacity_report
from src.review_operational_metrics import consolidate_review_metrics
from src.review_sla import apply_review_sla, render_review_sla_report
from tools.update_classified_history import load_events


def finalize_weekly_run(
    input_path: Path,
    *,
    history_path: Path = Path("history/classified_events.jsonl"),
    review_ledger_path: Path = Path("history/classification_reviews.jsonl"),
    review_backlog_path: Path = Path("history/review_backlog.json"),
    throughput_history_path: Path = Path("history/review_backlog_throughput.jsonl"),
    snapshots_dir: Path = Path("history/snapshots"),
    artifacts_dir: Path = Path("artifacts"),
    stale_after: int = STALE_AFTER_APPEARANCES,
    due_after_days: int = SLA_DUE_AFTER_DAYS,
    overdue_after_days: int = SLA_OVERDUE_AFTER_DAYS,
    overdue_after_appearances: int = SLA_OVERDUE_AFTER_APPEARANCES,
    capacity_lookback: int = CAPACITY_LOOKBACK_RUNS,
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

    prior_backlog = load_backlog(review_backlog_path)
    backlog, backlog_stats = reconcile_backlog(
        incoming_events,
        prior_backlog,
        stale_after=max(2, stale_after),
    )
    backlog, sla_stats = apply_review_sla(
        backlog,
        due_after_days=max(1, due_after_days),
        overdue_after_days=max(due_after_days + 1, overdue_after_days),
        overdue_after_appearances=max(2, overdue_after_appearances),
    )
    write_backlog(review_backlog_path, backlog)

    backlog_report_path = artifacts_dir / "review_backlog_report.txt"
    backlog_report_path.write_text(
        render_backlog_report(backlog, backlog_stats), encoding="utf-8"
    )
    sla_report_path = artifacts_dir / "review_sla_report.txt"
    sla_report_path.write_text(
        render_review_sla_report(backlog, sla_stats), encoding="utf-8"
    )

    throughput = analyze_backlog_throughput(prior_backlog, backlog)
    append_throughput(throughput_history_path, date.today().isoformat(), throughput)
    throughput_report_path = artifacts_dir / "review_backlog_throughput_report.txt"
    throughput_report_path.write_text(
        render_throughput_report(throughput), encoding="utf-8"
    )

    capacity = analyze_review_capacity(
        _load_jsonl_objects(throughput_history_path),
        active_backlog=len(backlog),
        lookback=max(1, capacity_lookback),
    )
    capacity_report_path = artifacts_dir / "review_capacity_report.txt"
    capacity_report_path.write_text(
        render_capacity_report(capacity), encoding="utf-8"
    )

    metrics = consolidate_review_metrics(backlog_stats, sla_stats, throughput, capacity)
    metrics_path = artifacts_dir / "review_operational_metrics.json"
    metrics_path.write_text(json.dumps(metrics.to_dict(), indent=2) + "\n", encoding="utf-8")

    review_batch_path = artifacts_dir / "classification_review_batch.csv"
    review_batch = export_review_batch(
        incoming_events,
        review_batch_path,
        reviewed_feedback=load_feedback(review_ledger_path),
        backlog=backlog,
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
        "review_backlog_path": str(review_backlog_path),
        "review_backlog_report": str(backlog_report_path),
        "review_backlog_active": metrics.active,
        "review_backlog_stale": metrics.stale,
        "review_backlog_trend": metrics.trend,
        "review_backlog_net_change": metrics.net_change,
        "review_backlog_throughput_report": str(throughput_report_path),
        "review_sla_report": str(sla_report_path),
        "review_sla_due_soon": metrics.due_soon,
        "review_sla_overdue": metrics.overdue,
        "review_sla_oldest_days": metrics.oldest_days,
        "review_capacity_report": str(capacity_report_path),
        "review_capacity_status": metrics.capacity_status,
        "review_capacity_net_clearance": metrics.net_clearance,
        "review_capacity_weeks_to_clear": metrics.weeks_to_clear,
        "review_operational_metrics": str(metrics_path),
        "review_metrics": metrics.to_dict(),
        "review_batch_path": str(review_batch_path),
        "review_batch_exported": review_batch.exported,
        "review_batch_skipped_reviewed": review_batch.skipped_already_reviewed,
        "report_failures": report_failures,
    }


def _load_jsonl_objects(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(value)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Final classified JSON or JSONL artifact")
    parser.add_argument("--history", type=Path, default=Path("history/classified_events.jsonl"))
    parser.add_argument("--review-ledger", type=Path, default=Path("history/classification_reviews.jsonl"))
    parser.add_argument("--review-backlog", type=Path, default=Path("history/review_backlog.json"))
    parser.add_argument("--throughput-history", type=Path, default=Path("history/review_backlog_throughput.jsonl"))
    parser.add_argument("--snapshots-dir", type=Path, default=Path("history/snapshots"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--stale-after", type=int, default=STALE_AFTER_APPEARANCES)
    parser.add_argument("--due-after-days", type=int, default=SLA_DUE_AFTER_DAYS)
    parser.add_argument("--overdue-after-days", type=int, default=SLA_OVERDUE_AFTER_DAYS)
    parser.add_argument("--overdue-after-appearances", type=int, default=SLA_OVERDUE_AFTER_APPEARANCES)
    parser.add_argument("--capacity-lookback", type=int, default=CAPACITY_LOOKBACK_RUNS)
    parser.add_argument("--skip-reports", action="store_true")
    args = parser.parse_args()

    result = finalize_weekly_run(
        args.input,
        history_path=args.history,
        review_ledger_path=args.review_ledger,
        review_backlog_path=args.review_backlog,
        throughput_history_path=args.throughput_history,
        snapshots_dir=args.snapshots_dir,
        artifacts_dir=args.artifacts_dir,
        stale_after=args.stale_after,
        due_after_days=args.due_after_days,
        overdue_after_days=args.overdue_after_days,
        overdue_after_appearances=args.overdue_after_appearances,
        capacity_lookback=args.capacity_lookback,
        run_reports=not args.skip_reports,
    )

    print("Attempt 94 Weekly Finalization")
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
        f"Review backlog: {result['review_backlog_path']} "
        f"({result['review_backlog_active']} active; {result['review_backlog_stale']} stale; "
        f"{result['review_backlog_trend']} {result['review_backlog_net_change']:+d})"
    )
    print(
        f"Review SLA: {result['review_sla_overdue']} overdue; "
        f"{result['review_sla_due_soon']} due soon; oldest={result['review_sla_oldest_days']}d"
    )
    eta = result["review_capacity_weeks_to_clear"]
    eta_text = "not clearing" if eta is None else f"{eta:.1f}w"
    print(
        f"Review capacity: {result['review_capacity_status']}; "
        f"net clearance={result['review_capacity_net_clearance']:+.1f}/week; ETA={eta_text}"
    )
    print(f"Review metrics: {result['review_operational_metrics']}")
    print(
        f"Review batch: {result['review_batch_path']} "
        f"({result['review_batch_exported']} events; "
        f"{result['review_batch_skipped_reviewed']} already reviewed)"
    )
    if result["report_failures"]:
        print("Non-blocking report failures: " + ", ".join(result["report_failures"]))


if __name__ == "__main__":
    main()
