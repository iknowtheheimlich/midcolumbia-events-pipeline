"""Report venue registry match coverage across generated harvest events."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from src.venue_registry import VenueRegistry


REGISTRY_PATH = Path("generated/venue_registry/registry.json")
HARVEST_ROOT = Path("generated/harvest")
REPORT_PATH = Path("generated/venue_registry/coverage_report.txt")


def main() -> None:
    if not REGISTRY_PATH.exists():
        raise SystemExit(
            "Venue registry artifact not found.\n"
            "Run the importer first after exporting Notion's Ultimate Venues database:\n"
            "  python -m tools.import_venue_registry\n"
            f"Expected artifact:\n  {REGISTRY_PATH}"
        )

    registry = VenueRegistry.from_json(REGISTRY_PATH)
    events: list[dict] = []
    for path in sorted(HARVEST_ROOT.glob("*/normalized_events.json")):
        events.extend(json.loads(path.read_text(encoding="utf-8")))

    if not events:
        raise SystemExit("No generated harvest events found.\nRun:\n  python -m tools.harvest_all")

    counts: Counter[str] = Counter()
    methods: Counter[str] = Counter()
    unknown: Counter[str] = Counter()
    ambiguous: Counter[str] = Counter()

    for event in events:
        venue = str(event.get("venue") or "").strip()
        match = registry.match_event(event)
        counts[match.status] += 1
        if match.status == "matched":
            methods[match.method or "unspecified"] += 1
        elif match.status == "unknown" and venue:
            unknown[venue] += 1
        elif match.status == "ambiguous" and venue:
            ambiguous[venue] += 1

    lines = [
        "Attempt_26 Venue Registry Coverage",
        "==================================",
        "",
        f"Registry records: {len(registry.records)}",
        f"Events scanned: {len(events)}",
        f"Matched: {counts['matched']}",
        f"Unknown: {counts['unknown']}",
        f"Ambiguous: {counts['ambiguous']}",
        f"Missing venue: {counts['missing']}",
        "",
        "Match methods:",
    ]
    if methods:
        lines.extend(f"  {count:>3}  {name}" for name, count in methods.most_common())
    else:
        lines.append("  none")

    lines.extend(["", "Unknown venues:"])
    if unknown:
        lines.extend(f"  {count:>3}  {name}" for name, count in unknown.most_common())
    else:
        lines.append("  none")

    lines.extend(["", "Ambiguous venues:"])
    if ambiguous:
        lines.extend(f"  {count:>3}  {name}" for name, count in ambiguous.most_common())
    else:
        lines.append("  none")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Registry records: {len(registry.records)}")
    print(f"Events scanned: {len(events)}")
    print(f"Matched: {counts['matched']}")
    print(f"Unknown: {counts['unknown']}")
    print(f"Ambiguous: {counts['ambiguous']}")
    if methods:
        print("Match methods: " + ", ".join(f"{name}={count}" for name, count in methods.most_common()))
    print(f"Saved report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
