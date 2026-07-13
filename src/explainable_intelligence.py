"""Compatibility helper delegating to the canonical intelligence contract."""

from __future__ import annotations

from typing import Any

from src.intelligence import attach_intelligence


def add_decision(
    event: dict[str, Any],
    field: str,
    value: Any,
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    """Attach one decision while preserving the legacy mutating call shape."""
    updated = attach_intelligence(event, field, value, confidence, reason)
    event.clear()
    event.update(updated)
    return event
