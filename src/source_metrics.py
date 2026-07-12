"""Operational telemetry for configured event sources.

Metrics are computed after a production run without changing event identity or
publisher decisions. A deduplicated event credits every contributing source for
coverage; duplicate removal credits only non-primary members of duplicate groups.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Any

from adapters.harvest import HarvestResult
from adapters.registry import AdapterInfo
from src.publisher_editorial import EditorialEvent


DEFAULT_SOURCE_METRICS_PATH = Path("artifacts/reddit/Source_Metrics.txt")


@dataclass(frozen=True)
class SourceMetrics:
    source_name: str
    enabled: bool
    priority: int
    status: str
    harvested: int = 0
    content_rejected: int = 0
    duplicates_removed: int = 0
    main_published: int = 0
    community_published: int = 0
    review: int = 0
    rejected: int = 0
    harvest_error: str | None = None



def build_source_metrics(
    adapters: Iterable[AdapterInfo],
    harvest_results: Iterable[HarvestResult],
    *,
    content_rejected_events: Iterable[Mapping[str, Any]] = (),
    duplicate_groups: Iterable[Mapping[str, Any]] = (),
    editorial_events: Iterable[EditorialEvent] = (),
) -> list[SourceMetrics]:
    """Return deterministic per-source metrics for one production run."""
    rows = {
        adapter.source_name: {
            "source_name": adapter.source_name,
            "enabled": adapter.enabled,
            "priority": adapter.priority,
            "status": adapter.status,
            "harvested": 0,
            "content_rejected": 0,
            "duplicates_removed": 0,
            "main_published": 0,
            "community_published": 0,
            "review": 0,
            "rejected": 0,
            "harvest_error": None,
        }
        for adapter in adapters
    }

    for result in harvest_results:
        row = rows.get(result.source_name)
        if row is None:
            continue
        row["harvested"] = result.normalized_count
        row["harvest_error"] = result.error

    for event in content_rejected_events:
        _increment(rows, str(event.get("source") or ""), "content_rejected")

    for group in duplicate_groups:
        source_events = group.get("source_events") or []
        for source_event in list(source_events)[1:]:
            if isinstance(source_event, Mapping):
                _increment(rows, str(source_event.get("source") or ""), "duplicates_removed")

    for event in editorial_events:
        sources = _event_sources(event)
        if event.publication_disposition == "AUTO_PUBLISH":
            if event.publication_target in {"MAIN", "BOTH"}:
                for source in sources:
                    _increment(rows, source, "main_published")
            if event.publication_target in {"COMMUNITY", "BOTH"}:
                for source in sources:
                    _increment(rows, source, "community_published")
        elif event.publication_disposition == "REVIEW":
            for source in sources:
                _increment(rows, source, "review")
        elif event.publication_disposition == "REJECT":
            for source in sources:
                _increment(rows, source, "rejected")

    return [
        SourceMetrics(**row)
        for row in sorted(rows.values(), key=lambda value: (-value["priority"], value["source_name"].casefold()))
    ]



def render_source_metrics(metrics: Iterable[SourceMetrics]) -> str:
    lines = ["Source Metrics", "==============", ""]
    for item in metrics:
        state = "enabled" if item.enabled else "disabled"
        lines.extend(
            [
                f"{item.source_name} [{state}; priority={item.priority}; status={item.status}]",
                f"  Harvested: {item.harvested}",
                f"  Content rejected: {item.content_rejected}",
                f"  Duplicates removed: {item.duplicates_removed}",
                f"  Main published: {item.main_published}",
                f"  Community published: {item.community_published}",
                f"  Review: {item.review}",
                f"  Rejected: {item.rejected}",
            ]
        )
        if item.harvest_error:
            lines.append(f"  Harvest warning: {item.harvest_error}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"



def write_source_metrics(
    metrics: Iterable[SourceMetrics],
    output_path: Path = DEFAULT_SOURCE_METRICS_PATH,
) -> Path:
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated source metrics must remain separate from fixtures")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_source_metrics(metrics), encoding="utf-8", newline="\n")
    return output_path



def _event_sources(event: EditorialEvent) -> tuple[str, ...]:
    ordered: list[str] = []
    for source in (event.source, *event.duplicate_sources):
        value = str(source or "").strip()
        if value and value not in ordered:
            ordered.append(value)
    return tuple(ordered)



def _increment(rows: dict[str, dict[str, Any]], source_name: str, field: str) -> None:
    source = source_name.strip()
    if source in rows:
        rows[source][field] += 1
