"""Report Eventbrite-linked events already discovered by active sources.

Attempt_24_Eventbrite_Bridge
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture
from adapters.eventbrite.bridge import bridge_items
from adapters.registry import AVAILABLE_ADAPTERS


GENERATED_ROOT = Path("generated/harvest")
OUTPUT_DIR = Path("generated/eventbrite_bridge")


def main() -> None:
    events: list[dict] = []
    source_counts: dict[str, int] = {}

    for adapter in sorted(AVAILABLE_ADAPTERS.values(), key=lambda item: item.source_name):
        generated_path = GENERATED_ROOT / adapter.source_name / "normalized_events.json"
        source_path = generated_path if generated_path.exists() else adapter.fixture_path
        payload = load_json_fixture(source_path)
        if not isinstance(payload, list):
            raise TypeError(f"normalized source must be a list: {source_path}")
        source_events = [event for event in payload if isinstance(event, dict)]
        source_counts[adapter.source_name] = len(source_events)
        events.extend(source_events)

    items = bridge_items(events)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_payload = [asdict(item) for item in items]
    (OUTPUT_DIR / "eventbrite_links.json").write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "Attempt_24 Eventbrite Bridge",
        "============================",
        "",
        f"Normalized events scanned: {len(events)}",
        f"Unique Eventbrite links: {len(items)}",
        "",
        "Source inputs:",
    ]
    lines.extend(f"  {name}: {count}" for name, count in sorted(source_counts.items()))
    lines.extend(["", "Review queue:"])

    if not items:
        lines.append("  No Eventbrite-linked events found in current harvested sources.")
    else:
        for item in items:
            when = " ".join(part for part in (item.start_date, item.start_time) if part) or "date unknown"
            place = ", ".join(part for part in (item.venue, item.city) if part) or "location unknown"
            lines.append(f"  {when} | {item.title or '(untitled)'} | {place}")
            lines.append(f"    source={item.source or 'unknown'} id={item.event_id or 'unknown'}")
            lines.append(f"    {item.eventbrite_url}")

    (OUTPUT_DIR / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Normalized events scanned: {len(events)}")
    print(f"Unique Eventbrite links: {len(items)}")
    print(f"Saved report under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
