"""Venue-level category priors loaded from the venue intelligence registry.

Attempt_73_VenueCategoryIntelligence

A venue hint is evidence, not a verdict. The category classifier decides when the
hint is eligible and keeps stronger title/source evidence ahead of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

_SPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "venue_category_hints.json"


@dataclass(frozen=True)
class VenueCategoryHint:
    venue_name: str
    category: str
    confidence: float
    strength: str


def normalize_venue_name(value: Any) -> str:
    text = str(value or "").casefold().replace("&", " and ")
    text = _NON_ALNUM_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


@lru_cache(maxsize=4)
def load_venue_category_hints(path: str | None = None) -> dict[str, VenueCategoryHint]:
    registry_path = Path(path) if path else _DEFAULT_PATH
    if not registry_path.exists():
        return {}

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    hints: dict[str, VenueCategoryHint] = {}
    for venue_name, raw in payload.items():
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category_hint") or "").strip()
        if not category:
            continue
        confidence = float(raw.get("category_confidence") or 0.0)
        strength = str(raw.get("hint_strength") or "soft").strip().casefold()
        if strength not in {"strong", "soft"}:
            strength = "soft"
        hint = VenueCategoryHint(
            venue_name=str(venue_name).strip(),
            category=category,
            confidence=max(0.0, min(confidence, 1.0)),
            strength=strength,
        )
        hints[normalize_venue_name(venue_name)] = hint
    return hints


def venue_category_hint(event: dict[str, Any]) -> VenueCategoryHint | None:
    """Return the canonical venue prior for an enriched event, when one exists."""
    candidates = (
        event.get("venue_registry_name"),
        event.get("venue"),
        event.get("display_venue"),
        event.get("parent_display_name"),
    )
    hints = load_venue_category_hints()
    for candidate in candidates:
        key = normalize_venue_name(candidate)
        if key and key in hints:
            return hints[key]
    return None
