"""Report obvious non-event content across generated harvest output."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from src.content_classifier import classify_content
from src.text_normalization import normalize_event


HARVEST_ROOT = Path("generated/harvest")
REPORT_PATH = Path("generated/content_screening/report.txt")


def main() -> None:
    events: list[dict] = []
    for path in sorted(HARVEST_ROOT.glob("*/normalized_events.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        events.extend(normalize_event(event) for event in payload)

    if not events:
        raise SystemExit("No generated harvest events found.\nRun:\n  python -m tools.harvest_all")

    kinds: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    rejected: list[tuple[str, str, str, str]] = []

    for event in events:
        classification = classify_content(event)
        kinds[classification.kind] += 1
        if not classification.publishable:
            reason = classification.reason or "unspecified"
            reasons[reason] += 1
            rejected.append(
                (
                    str(event.get("source") or "(unknown source)"),
                    str(event.get("title") or "(untitled)"),
                    str(event.get("venue") or "(no venue)"),
                    reason,
                )
            )

    lines = [
        "Attempt_28 Content Screening",
        "============================",
        "",
        f"Items scanned: {len(events)}",
        f"Publishable: {sum(count for kind, count in kinds.items() if kind == 'EVENT')}",
        f"Rejected: {len(rejected)}",
        "",
        "Classification counts:",
    ]
    lines.extend(f"  {count:>3}  {kind}" for kind, count in kinds.most_common())

    lines.extend(["", "Rejection reasons:"])
    if reasons:
        lines.extend(f"  {count:>3}  {reason}" for reason, count in reasons.most_common())
    else:
        lines.append("  none")

    lines.extend(["", "Rejected items:"])
    if rejected:
        for source, title, venue, reason in sorted(rejected):
            lines.append(f"  [{reason}] {source} | {title} | {venue}")
    else:
        lines.append("  none")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Items scanned: {len(events)}")
    print(f"Rejected: {len(rejected)}")
    if reasons:
        print("Reasons: " + ", ".join(f"{name}={count}" for name, count in reasons.most_common()))
    print(f"Saved report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
