"""Common explainable-intelligence contract for inferred event fields.

Attempt_42_ExplainableIntelligence

Flat event fields remain authoritative for backwards compatibility. The additive
``intelligence`` mapping records how inferred values were produced.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class IntelligenceDecision:
    value: Any
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def attach_intelligence(
    event: Mapping[str, Any],
    field: str,
    value: Any,
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    """Return a copied event with one additive intelligence decision."""
    copied = dict(event)
    existing = copied.get("intelligence")
    intelligence = dict(existing) if isinstance(existing, Mapping) else {}
    intelligence[field] = IntelligenceDecision(
        value=value,
        confidence=_bounded_confidence(confidence),
        reason=str(reason).strip() or "unspecified",
    ).to_dict()
    copied["intelligence"] = intelligence
    return copied


def read_intelligence(event: Mapping[str, Any], field: str) -> IntelligenceDecision | None:
    """Read one decision from an event-like mapping."""
    intelligence = event.get("intelligence")
    if not isinstance(intelligence, Mapping):
        return None
    payload = intelligence.get(field)
    if not isinstance(payload, Mapping):
        return None
    try:
        return IntelligenceDecision(
            value=payload.get("value"),
            confidence=_bounded_confidence(float(payload.get("confidence", 0.0))),
            reason=str(payload.get("reason") or "unspecified"),
        )
    except (TypeError, ValueError):
        return None


def normalize_intelligence(value: Any) -> dict[str, dict[str, Any]]:
    """Return a defensive JSON-safe copy of an intelligence mapping."""
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for field, payload in value.items():
        if not isinstance(payload, Mapping):
            continue
        decision = read_intelligence({"intelligence": {str(field): payload}}, str(field))
        if decision is not None:
            result[str(field)] = decision.to_dict()
    return result


def _bounded_confidence(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)
