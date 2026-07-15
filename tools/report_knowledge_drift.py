"""Generate a read-only knowledge drift report for active venue and organizer hints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.knowledge_drift import detect_knowledge_drift
from src.organizer_category_intelligence import load_organizer_category_hints
from src.venue_category_intelligence import load_venue_category_hints


def load_events(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("events", "all_events", "publisher_ready_events", "deduplicated_publisher_ready_events"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    raise ValueError(f"No event list found in {path}")


def render_report(results) -> str:
    statuses = ("DRIFT", "WATCH", "STABLE", "INSUFFICIENT")
    counts = {status: sum(item.status == status for item in results) for status in statuses}
    lines = [
        "Attempt 76 Knowledge Drift Detection",
        "====================================",
        "",
        f"Hints analyzed: {len(results)}",
        f"Drift: {counts['DRIFT']}",
        f"Watch: {counts['WATCH']}",
        f"Stable: {counts['STABLE']}",
        f"Insufficient evidence: {counts['INSUFFICIENT']}",
        "",
    ]
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
    parser.add_argument("input", type=Path, help="JSON event history with final categories")
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--minimum-recent-events", type=int, default=5)
    parser.add_argument("--json-output", type=Path, default=Path("artifacts/knowledge_drift.json"))
    parser.add_argument("--report-output", type=Path, default=Path("artifacts/knowledge_drift_report.txt"))
    args = parser.parse_args()

    results = detect_knowledge_drift(
        load_events(args.input),
        venue_hints=load_venue_category_hints(),
        organizer_hints=load_organizer_category_hints(),
        recent_limit=args.recent_limit,
        minimum_recent_events=args.minimum_recent_events,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps([item.to_dict() for item in results], indent=2) + "\n", encoding="utf-8")
    report = render_report(results)
    args.report_output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
