"""Recover useful event details buried in descriptive text.

Attempt_56_SupplementalDetailRecovery

Structured source fields remain authoritative. This layer only fills missing cost
information and extracts labeled schedule assignments without changing canonical
start/end times.
"""

from __future__ import annotations

import re
from typing import Any

from src.intelligence import attach_intelligence

_SPACE_RE = re.compile(r"\s+")
_TIME_RE = re.compile(r"\b(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*(?:a\.?m\.?|p\.?m\.?)\b", re.IGNORECASE)
_FREE_RE = re.compile(r"\b(?:free|no charge|no cost|free admission)\b", re.IGNORECASE)
_PRICE_RE = re.compile(
    r"(?:\$\s?\d+(?:\.\d{2})?(?:\s*(?:-|–|to)\s*\$?\s?\d+(?:\.\d{2})?)?|"
    r"\b(?:admission|tickets?|price|cost)\s*(?::|is|are|-)?\s*\$\s?\d+(?:\.\d{2})?)",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(r"(?:\r?\n|\s+[•·|]\s+|(?<=[.!?;])\s+)")


def enrich_event_supplemental_details(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy enriched with conservative description-level recovery."""
    result = dict(event)
    description = _clean(result.get("description"))
    if not description:
        return result

    if not _clean(result.get("cost")):
        recovered_cost = extract_cost(description)
        if recovered_cost:
            result["cost"] = recovered_cost
            result["cost_source"] = "description"
            confidence = 0.98 if recovered_cost.casefold() == "Free" else 0.92
            result = attach_intelligence(
                result,
                "cost",
                recovered_cost,
                confidence,
                "description_cost_recovery",
            )

    if not result.get("schedule_items"):
        schedule_items = extract_schedule_items(description)
        if schedule_items:
            result["schedule_items"] = schedule_items
            result["schedule_source"] = "description"
            result = attach_intelligence(
                result,
                "schedule_items",
                schedule_items,
                0.90,
                "description_labeled_time_recovery",
            )

    return result


def extract_cost(text: str) -> str | None:
    """Extract a concise admission value from descriptive text."""
    cleaned = _clean(text)
    if not cleaned:
        return None
    if _FREE_RE.search(cleaned):
        return "Free"
    match = _PRICE_RE.search(cleaned)
    if not match:
        return None
    value = _clean(match.group(0))
    price = re.search(r"\$\s?\d+(?:\.\d{2})?(?:\s*(?:-|–|to)\s*\$?\s?\d+(?:\.\d{2})?)?", value)
    return _clean(price.group(0)).replace("$ ", "$") if price else value


def extract_schedule_items(text: str) -> list[dict[str, str]]:
    """Extract labeled time assignments while rejecting bare event-time mentions."""
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for segment in _SPLIT_RE.split(str(text or "")):
        cleaned = _clean(segment)
        match = _TIME_RE.search(cleaned)
        if not match:
            continue
        before = cleaned[: match.start()].strip(" :-–—")
        after = cleaned[match.end() :].strip(" :-–—")
        label = before or after
        if not label or len(label) < 3:
            continue
        label = _clean(label)
        if label.casefold() in {"event", "starts", "start", "time"}:
            continue
        item = {"time": _normalize_time(match.group(0)), "label": label[:160], "source": cleaned[:240]}
        identity = (item["time"].casefold(), item["label"].casefold())
        if identity in seen:
            continue
        seen.add(identity)
        items.append(item)
    return items


def _normalize_time(value: str) -> str:
    cleaned = value.upper().replace(".", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()
