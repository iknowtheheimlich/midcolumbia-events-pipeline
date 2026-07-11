"""Report geographic classification across generated harvest events."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from src.geography import classify_event
from src.text_normalization import normalize_event


HARVEST_ROOT = Path("generated/harvest")
REPORT_PATH = Path("generated/geographic_intelligence/report.txt")


def main() -> None:
    events: list[dict] = []
    for path in sorted(HARVEST_ROOT.glob("*/normalized_events.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        events.extend(normalize_event(event) for event in payload)

    if not events:
        raise SystemExit("No generated harvest events found.\nRun:\n  python -m tools.harvest_all")

    region_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    city_counts: Counter[str] = Counter()
    out_of_area: list[tuple[str, str, str, str]] = []
    review: list[tuple[str, str, str]] = []

    for event in events:
        result = classify_event(event)
        region_counts[result.region] += 1
        scope_counts[result.scope] += 1
        city_counts[result.city or "(unknown)"] += 1

        title = str(event.get("title") or "(untitled)")
        venue = str(event.get("venue") or "(no venue)")
        if result.scope == "OUT_OF_AREA":
            out_of_area.append((result.city or "(unknown)", result.region, title, venue))
        elif result.scope == "REVIEW":
            review.append((title, venue, str(event.get("address") or "")))

    lines = [
        "Attempt_27 Geographic Intelligence",
        "===================================",
        "",
        f"Events scanned: {len(events)}",
        "",
        "Scope counts:",
    ]
    lines.extend(f"  {count:>3}  {name}" for name, count in scope_counts.most_common())

    lines.extend(["", "Region counts:"])
    lines.extend(f"  {count:>3}  {name}" for name, count in region_counts.most_common())

    lines.extend(["", "Top normalized cities:"])
    lines.extend(f"  {count:>3}  {name}" for name, count in city_counts.most_common(30))

    lines.extend(["", "Out-of-area review queue:"])
    if out_of_area:
        for city, region, title, venue in sorted(out_of_area):
            lines.append(f"  [{region}] {city} | {title} | {venue}")
    else:
        lines.append("  none")

    lines.extend(["", "Unknown-location review queue:"])
    if review:
        for title, venue, address in sorted(review):
            suffix = f" | {address}" if address else ""
            lines.append(f"  {title} | {venue}{suffix}")
    else:
        lines.append("  none")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Events scanned: {len(events)}")
    print("Scopes: " + ", ".join(f"{name}={count}" for name, count in scope_counts.most_common()))
    print("Regions: " + ", ".join(f"{name}={count}" for name, count in region_counts.most_common()))
    print(f"Saved report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
