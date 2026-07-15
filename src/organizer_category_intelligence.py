"""Organizer-level category priors.

Attempt_75_OrganizerCategoryIntelligence

Organizer hints travel with the organizer across venues. They are evidence, not verdicts,
and never outrank explicit title or source-category evidence.
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
_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "organizer_category_hints.json"


@dataclass(frozen=True)
class OrganizerCategoryHint:
    organizer_name: str
    category: str
    confidence: float
    strength: str


def normalize_organizer_name(value: Any) -> str:
    text = str(value or "").casefold().replace("&", " and ")
    text = _NON_ALNUM_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


@lru_cache(maxsize=4)
def load_organizer_category_hints(path: str | None = None) -> dict[str, OrganizerCategoryHint]:
    registry_path = Path(path) if path else _DEFAULT_PATH
    if not registry_path.exists():
        return {}

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    hints: dict[str, OrganizerCategoryHint] = {}
    for organizer_name, raw in payload.items():
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category_hint") or "").strip()
        if not category:
            continue
        confidence = float(raw.get("category_confidence") or 0.0)
        strength = str(raw.get("hint_strength") or "soft").strip().casefold()
        if strength not in {"strong", "soft"}:
            strength = "soft"
        hint = OrganizerCategoryHint(
            organizer_name=str(organizer_name).strip(),
            category=category,
            confidence=max(0.0, min(confidence, 1.0)),
            strength=strength,
        )
        keys = [organizer_name, *(raw.get("aliases") or [])]
        for key in keys:
            normalized = normalize_organizer_name(key)
            if normalized:
                hints[normalized] = hint
    return hints


def organizer_category_hint(event: dict[str, Any]) -> OrganizerCategoryHint | None:
    """Return an organizer prior from canonical or source organizer fields."""
    candidates = (
        event.get("organizer_registry_name"),
        event.get("organization"),
        event.get("organizer"),
        event.get("host"),
        event.get("presented_by"),
    )
    hints = load_organizer_category_hints()
    for candidate in candidates:
        key = normalize_organizer_name(candidate)
        if key and key in hints:
            return hints[key]
    return None
