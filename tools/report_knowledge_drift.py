"""Generate a read-only knowledge drift report for active venue and organizer hints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.event_io import load_event_records
from src.knowledge_drift import detect_knowledge_drift
from src.organizer_category_intelligence import load_organizer_category_hints
from src.venue_category_intelligence import load_venue_category_hints


def load_events(path: Path) -> list[dict]:
    """Backward-compatible alias for the canonical event loader."""
    return load_event_records(path)


def classified_events(events: list[dict]) -> list[dict]:
    return [row for row in events if str(row.get("category") or "").strip()]


def render_report(results, *, loaded_events: int, classified_event_count: int) -> str:
    statuses = ("DRIFT", "WATCH", "STABLE", "INSUFFICIENT")
    counts = {status: sum(item.status == status for item in results) for status in statuses}
    lines = [
        "Attempt 76 Knowledge Drift Detection",
        "====================================",
        "",
        f"Events loaded: {loaded_events}",
        f"Classified events eligible: {classified_event_count}",
        f"Canonical hints analyzed: {len(results)}",
        f"Drift: {counts['DRIFT']}",
        f"Watch: {counts['WATCH']}",
        f"Stable: {counts['STABLE']}",
        f"Insufficient evidence: {counts['INSUFFICIENT']}",
        "",
    ]
    if classified_event_count == 0:
        lines.extend([
            "INPUT NOT SUITABLE FOR DRIFT ANALYSIS",
            "-------------------------------------",
            "",
            "No events contain a final category. Use accumulated classified history, not a raw or pre-enrichment fixture.",
            "",
        ])
    for status in statuses:
        title = "INSUFFICIENT EVIDENCE" if status == "INSUFFICIENT" else status
        lines.extend([title, "-" * len(title), ""])
        matching = [item for item in results if item.status == status]
        if not matching:
            lines.extend(["None", ""])
            continue
        for item in matching:
            lines.append(f"{item.entity_type.title()}: {item.entity_name}")
            lines.append(f"  Expected: {item.expected_category}")
            lines.append(f"  Recent events: {item.recent_events}")
            lines.append(f"  Expected share: {item.expected_percent:.1%}")
            lines.append(f"  Recent dominant: {item.dominant_category or 'None'} ({item.dominant_percent:.1%})")
            lines.append(f"  Change magnitude: {item.change_magnitude:.1%}")
            lines.append(f"  Recommendation: {item.recommendation}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON or JSONL event history with final categories")
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--minimum-recent-events", type=int, default=5)
    parser.add_argument("--json-output", type=Path, default=Path("artifacts/knowledge_drift.json"))
    parser.add_argument("--report-output", type=Path, default=Path("artifacts/knowledge_drift_report.txt"))
    args = parser.parse_args()

    loaded = load_event_records(args.input)
    eligible = classified_events(loaded)
    results = detect_knowledge_drift(
        eligible,
        venue_hints=load_venue_category_hints(),
        organizer_hints=load_organizer_category_hints(),
        recent_limit=args.recent_limit,
        minimum_recent_events=args.minimum_recent_events,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps([item.to_dict() for item in results], indent=2) + "\n", encoding="utf-8")
    report = render_report(results, loaded_events=len(loaded), classified_event_count=len(eligible))
    args.report_output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
