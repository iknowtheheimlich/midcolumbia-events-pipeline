"""Translate live production state into Mid-Columbia Mission Control artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.mission_archive import write_mission_artifacts
from src.mission_control import MissionControlReport, SourceHealthSummary, build_mission_control_report

DEFAULT_CORPUS_SUMMARY = Path("generated/corpus/summary.json")


def write_production_mission_control(
    *,
    week_start: str,
    production_status: str,
    source_health: Iterable[Any],
    source_durations_ms: Mapping[str, int],
    counts: Mapping[str, int],
    artifacts: Mapping[str, str | Path],
    warnings: Iterable[str] = (),
    corpus_summary_path: Path = DEFAULT_CORPUS_SUMMARY,
) -> tuple[MissionControlReport, dict[str, Path]]:
    """Build and archive Mission Control output from objects already in memory."""
    sources = tuple(
        SourceHealthSummary(
            source=str(getattr(item, "source_name", "Unknown")),
            status=_mission_source_status(str(getattr(item, "status", "UNKNOWN"))),
            harvested=int(getattr(item, "event_count", 0)),
            reason=getattr(item, "reason", None),
            duration_ms=source_durations_ms.get(str(getattr(item, "source_name", ""))),
        )
        for item in source_health
    )
    report = build_mission_control_report(
        week_start=week_start,
        production_status=_mission_production_status(production_status),
        source_health=sources,
        counts=counts,
        knowledge=_load_knowledge_counts(corpus_summary_path),
        warnings=warnings,
        artifacts=artifacts,
        regression={"passed": None, "reason": "runtime suite not executed by publisher"},
    )
    return report, write_mission_artifacts(report)


def _mission_source_status(value: str) -> str:
    status = value.upper()
    if status in {"LIVE", "OPTIONAL"}:
        return "HEALTHY"
    if status == "CACHED":
        return "CACHED"
    return status


def _mission_production_status(value: str) -> str:
    return "HEALTHY" if value.upper() == "HEALTHY" else value.upper()


def _load_knowledge_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    aliases = {
        "historical_events": "historical_events",
        "venues": "venues",
        "hosts": "hosts",
        "artist_candidates": "artist_candidates",
        "recurring_families": "recurring_families",
    }
    counts: dict[str, int] = {}
    for source_key, output_key in aliases.items():
        value = payload.get(source_key)
        if isinstance(value, int):
            counts[output_key] = value
    return counts
