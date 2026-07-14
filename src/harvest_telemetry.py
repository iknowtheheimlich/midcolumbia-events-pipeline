"""Append-only per-source harvest telemetry.

Attempt_54_HarvestTelemetry
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping

from adapters.harvest import HarvestResult
from src.harvest_health import HarvestHealthReport

DEFAULT_HARVEST_TELEMETRY_PATH = Path("artifacts/telemetry/Harvest_History.jsonl")


def build_harvest_telemetry_records(
    health: HarvestHealthReport,
    results: Iterable[HarvestResult],
    durations_ms: Mapping[str, int],
    *,
    timestamp: datetime | None = None,
) -> list[dict[str, object]]:
    """Build one durable telemetry record per harvested source."""
    observed_at = timestamp or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    timestamp_text = observed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    health_by_source = {item.source_name: item for item in health.sources}
    records: list[dict[str, object]] = []
    for result in results:
        item = health_by_source[result.source_name]
        records.append(
            {
                "timestamp": timestamp_text,
                "source": result.source_name,
                "status": item.status,
                "required": item.required,
                "events": result.normalized_count,
                "duration_ms": int(durations_ms.get(result.source_name, 0)),
                "reused_fixture": result.reused_normalized,
                "error": result.error,
            }
        )
    return records


def append_harvest_telemetry(records: Iterable[Mapping[str, object]], path: Path) -> None:
    """Append JSONL records without rewriting prior harvest history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
