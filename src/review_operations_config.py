"""Typed configuration for classification-review operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Mapping

from src.operational_defaults import (
    CAPACITY_LOOKBACK_RUNS,
    SLA_DUE_AFTER_DAYS,
    SLA_OVERDUE_AFTER_APPEARANCES,
    SLA_OVERDUE_AFTER_DAYS,
    STALE_AFTER_APPEARANCES,
)


@dataclass(frozen=True)
class ReviewOperationsConfig:
    stale_after_appearances: int = STALE_AFTER_APPEARANCES
    sla_due_after_days: int = SLA_DUE_AFTER_DAYS
    sla_overdue_after_days: int = SLA_OVERDUE_AFTER_DAYS
    sla_overdue_after_appearances: int = SLA_OVERDUE_AFTER_APPEARANCES
    capacity_lookback_runs: int = CAPACITY_LOOKBACK_RUNS

    def __post_init__(self) -> None:
        if self.stale_after_appearances < 2:
            raise ValueError("stale_after_appearances must be at least 2")
        if self.sla_due_after_days < 1:
            raise ValueError("sla_due_after_days must be at least 1")
        if self.sla_overdue_after_days <= self.sla_due_after_days:
            raise ValueError("sla_overdue_after_days must exceed sla_due_after_days")
        if self.sla_overdue_after_appearances < 2:
            raise ValueError("sla_overdue_after_appearances must be at least 2")
        if self.capacity_lookback_runs < 1:
            raise ValueError("capacity_lookback_runs must be at least 1")

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    def with_overrides(
        self,
        *,
        stale_after: int | None = None,
        due_after_days: int | None = None,
        overdue_after_days: int | None = None,
        overdue_after_appearances: int | None = None,
        capacity_lookback: int | None = None,
    ) -> "ReviewOperationsConfig":
        values: dict[str, int] = {}
        if stale_after is not None:
            values["stale_after_appearances"] = stale_after
        if due_after_days is not None:
            values["sla_due_after_days"] = due_after_days
        if overdue_after_days is not None:
            values["sla_overdue_after_days"] = overdue_after_days
        if overdue_after_appearances is not None:
            values["sla_overdue_after_appearances"] = overdue_after_appearances
        if capacity_lookback is not None:
            values["capacity_lookback_runs"] = capacity_lookback
        return replace(self, **values)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ReviewOperationsConfig":
        allowed = set(cls.__dataclass_fields__)
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"Unknown review configuration keys: {', '.join(unknown)}")
        values: dict[str, int] = {}
        for key, value in payload.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"Review configuration value for {key} must be an integer")
            values[key] = value
        return cls(**values)


def load_review_operations_config(path: Path | None) -> ReviewOperationsConfig:
    if path is None:
        return ReviewOperationsConfig()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid review configuration JSON in {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Review configuration in {path} must be a JSON object")
    return ReviewOperationsConfig.from_mapping(payload)
