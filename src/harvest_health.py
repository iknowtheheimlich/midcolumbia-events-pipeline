"""Production harvest health classification and publication gating.

Attempt_53_HarvestHealthGate
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from adapters.harvest import HarvestResult
from adapters.registry import AdapterInfo

DEGRADED_ROOT = Path("artifacts/degraded")


@dataclass(frozen=True)
class SourceHarvestHealth:
    source_name: str
    status: str
    required: bool
    event_count: int
    reason: str | None = None


@dataclass(frozen=True)
class HarvestHealthReport:
    sources: tuple[SourceHarvestHealth, ...]

    @property
    def degraded(self) -> bool:
        return any(item.required and item.status != "LIVE" for item in self.sources)

    @property
    def failed_required_sources(self) -> tuple[SourceHarvestHealth, ...]:
        return tuple(item for item in self.sources if item.required and item.status != "LIVE")

    @property
    def status(self) -> str:
        return "DEGRADED" if self.degraded else "HEALTHY"


def assess_harvest_health(
    adapters: Iterable[AdapterInfo],
    results: Iterable[HarvestResult],
) -> HarvestHealthReport:
    adapter_map = {adapter.source_name: adapter for adapter in adapters}
    items: list[SourceHarvestHealth] = []
    for result in results:
        adapter = adapter_map[result.source_name]
        required = adapter.status == "active"
        if result.error:
            status = "PARTIAL" if result.normalized_events else "FAILED"
            reason = result.error
        elif result.reused_normalized:
            status = "CACHED"
            reason = "normalized fixture reused"
        else:
            status = "LIVE"
            reason = None
        if not required and status != "FAILED":
            status = "OPTIONAL"
        items.append(
            SourceHarvestHealth(
                source_name=result.source_name,
                status=status,
                required=required,
                event_count=result.normalized_count,
                reason=reason,
            )
        )
    return HarvestHealthReport(tuple(items))


def degraded_artifact_path(path: Path, root: Path = DEGRADED_ROOT) -> Path:
    """Return a separate degraded-output path without mutating the production artifact."""
    return root / path.name
