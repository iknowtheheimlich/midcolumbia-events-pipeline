"""Generate venue category-prior candidates from classified event history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.venue_intelligence_discovery import discover_venue_intelligence


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


def render_report(candidates) -> str:
    counts = {name: sum(item.recommendation == name for item in candidates) for name in ("PROMOTE", "REVIEW", "REJECT")}
    lines = [
        "Attempt 74 Venue Intelligence Discovery",
        "=======================================",
        "",
        f"Venues analyzed: {len(candidates)}",
        f"Promote: {counts['PROMOTE']}",
        f"Review: {counts['REVIEW']}",
        f"Reject: {counts['REJECT']}",
        "",
    ]
    for recommendation in ("PROMOTE", "REVIEW", "REJECT"):
        lines.extend([recommendation, "-" * len(recommendation), ""])
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
    parser.add_argument("input", type=Path, help="JSON event history with final categories")
    parser.add_argument("--json-output", type=Path, default=Path("artifacts/venue_intelligence_candidates.json"))
    parser.add_argument("--report-output", type=Path, default=Path("artifacts/venue_intelligence_report.txt"))
    parser.add_argument("--minimum-events", type=int, default=25)
    args = parser.parse_args()

    candidates = discover_venue_intelligence(load_events(args.input), minimum_events=args.minimum_events)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps([item.to_dict() for item in candidates], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.report_output.write_text(render_report(candidates), encoding="utf-8")
    print(render_report(candidates), end="")


if __name__ == "__main__":
    main()
