"""Compatibility helpers for the additive explainable-intelligence mapping."""

from __future__ import annotations

from typing import Any


def add_decision(
    event: dict[str, Any],
    field: str,
    value: Any,
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    """Add one JSON-safe intelligence decision without changing flat fields."""
    intelligence = dict(event.get("intelligence") or {})
    intelligence[field] = {
        "value": value,
        "confidence": float(confidence),
        "reason": str(reason),
    }
    event["intelligence"] = intelligence
    return event
