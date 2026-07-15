"""Generate venue category-prior candidates from accumulated classified event history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.venue_intelligence_discovery import discover_venue_intelligence


def load_events(path: Path) -> list[dict]:
    if path.is_dir():
        rows: list[dict] = []
        for child in sorted(path.rglob("*.json")):
            rows.extend(load_events(child))
        for child in sorted(path.rglob("*.jsonl")):
            rows.extend(load_events(child))
        return rows

    if path.suffix.casefold() == ".jsonl":
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        return rows

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("events", "all_events", "publisher_ready_events", "deduplicated_publisher_ready_events"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    raise ValueError(f"No event list found in {path}")


def load_history(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        rows.extend(load_events(path))
    return rows


def render_report(candidates, *, history_events: int = 0, input_count: int = 0) -> str:
    names = ("PROMOTE", "REVIEW", "INSUFFICIENT", "REJECT")
    counts = {name: sum(item.recommendation == name for item in candidates) for name in names}
    lines = [
        "Attempt 74 Venue Intelligence Discovery",
        "=======================================",
        "",
        f"History inputs: {input_count}",
        f"Historical events loaded: {history_events}",
        f"Venues analyzed: {len(candidates)}",
        f"Promote: {counts['PROMOTE']}",
        f"Review: {counts['REVIEW']}",
        f"Insufficient evidence: {counts['INSUFFICIENT']}",
        f"Reject: {counts['REJECT']}",
        "",
    ]
    for recommendation in names:
        heading = "INSUFFICIENT EVIDENCE" if recommendation == "INSUFFICIENT" else recommendation
        lines.extend([heading, "-" * len(heading), ""])
        matching = [item for item in candidates if item.recommendation == recommendation]
        if not matching:
            lines.extend(["None", ""])
            continue
        for item in matching:
            lines.append(item.venue_name)
            lines.append(f"  Dominant: {item.dominant_category or 'Unknown'} ({item.dominant_percent:.1%})")
            lines.append(f"  Events: {item.total_events}")
            lines.append(f"  Second: {item.second_category or 'None'} ({item.second_percent:.1%})")
            lines.append(f"  Entropy: {item.entropy:.3f}")
            lines.append(f"  Confidence: {item.confidence:.3f}")
            if item.venue_type:
                lines.append(f"  Venue type: {item.venue_type}")
            if item.last_seen:
                lines.append(f"  Last seen: {item.last_seen}")
            lines.append(f"  Reason: {item.reason}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more JSON/JSONL history files or directories containing classified events",
    )
    parser.add_argument("--json-output", type=Path, default=Path("artifacts/venue_intelligence_candidates.json"))
    parser.add_argument("--report-output", type=Path, default=Path("artifacts/venue_intelligence_report.txt"))
    parser.add_argument("--minimum-events", type=int, default=25)
    args = parser.parse_args()

    history = load_history(args.inputs)
    candidates = discover_venue_intelligence(history, minimum_events=args.minimum_events)
    report = render_report(candidates, history_events=len(history), input_count=len(args.inputs))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps([item.to_dict() for item in candidates], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.report_output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
