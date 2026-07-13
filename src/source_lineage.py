"""Source lineage enrichment for native and syndicated event records.

Attempt_52_SourceLineage

``source`` remains the compatibility discovery-source field. ``origin_source`` records
who authored or owns the event, while ``discovery_source`` records where this copy was
harvested. Syndicated copies are not independent corroboration.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from src.intelligence import attach_intelligence

_SPACE_RE = re.compile(r"\s+")


def enrich_event_source_lineage(event: dict[str, Any]) -> dict[str, Any]:
    copied = dict(event)
    discovery = _text(copied.get("discovery_source") or copied.get("source"))
    origin = _text(copied.get("origin_source")) or discovery
    reason = "native_source"
    confidence = 1.0

    if discovery == "AllEvents" and _looks_like_richland_library(copied):
        origin = "RichlandLibrary"
        reason = "syndicated_richland_library_via_allevents"
        confidence = 0.98

    if discovery:
        copied["discovery_source"] = discovery
    if origin:
        copied["origin_source"] = origin
    copied["is_syndicated"] = bool(discovery and origin and discovery != origin)

    return attach_intelligence(
        copied,
        "source_lineage",
        {"origin_source": origin, "discovery_source": discovery},
        confidence,
        reason,
    )


def enrich_event_source_lineages(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_event_source_lineage(event) for event in events]


def _looks_like_richland_library(event: dict[str, Any]) -> bool:
    values = (
        event.get("venue"),
        event.get("venue_registry_name"),
        event.get("organization"),
        event.get("organizer"),
        event.get("host"),
        event.get("external_url"),
    )
    haystack = " | ".join(_text(value) or "" for value in values).casefold()
    return any(
        marker in haystack
        for marker in (
            "richland public library",
            "richland library",
            "myrichlandlibrary.libcal.com",
        )
    )


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = _SPACE_RE.sub(" ", str(value).strip())
    return text or None
