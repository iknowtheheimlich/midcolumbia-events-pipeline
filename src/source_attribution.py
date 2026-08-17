"""Publication attribution and conservative source-evidence quarantine."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from adapters.registry import AdapterInfo
from src.intelligence import attach_intelligence

_STOP = {"the", "a", "an", "at", "in", "on", "event", "events", "live", "winery", "wines"}
DEFAULT_ATTRIBUTION_PREFIX = "This is not an all inclusive list. Events were extracted from"


def build_source_attribution(
    adapters: Iterable[AdapterInfo], *, prefix: str = DEFAULT_ATTRIBUTION_PREFIX,
) -> str:
    labels = [
        adapter.attribution_label for adapter in adapters
        if adapter.include_in_attribution and adapter.attribution_label
    ]
    labels = list(dict.fromkeys(labels))
    if not labels:
        return ""
    return f"{prefix} {_join_labels(labels)}."


def _join_labels(labels: list[str]) -> str:
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def quarantine_attribution_conflicts(event: dict[str, Any]) -> dict[str, Any]:
    copied = dict(event)
    reasons: list[str] = []
    source_id = str(copied.get("source_event_id") or "")
    title = str(copied.get("title") or "")
    if "-at-" in source_id.casefold() and " at " in title.casefold():
        id_subject = _tokens(source_id.casefold().split("-at-", 1)[0])
        title_subject = _tokens(re.split(r"\s+at\s+", title, maxsplit=1, flags=re.IGNORECASE)[0])
        if len(id_subject) >= 2 and len(title_subject) >= 2 and id_subject.isdisjoint(title_subject):
            reasons.append("source_id_title_subject_conflict")

    if reasons:
        copied["publication_blocker_reason"] = "source_attribution_conflict"
        copied["publication_blocker_details"] = tuple(
            list(copied.get("publication_blocker_details") or ())
            + [{"source": copied.get("source"), "reason": reason} for reason in reasons]
        )
    return attach_intelligence(copied, "source_attribution", reasons or ["consistent"], 1.0, "+".join(reasons) if reasons else "consistent")


def _tokens(value: Any) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", str(value or "").casefold()) if len(token) > 1 and token not in _STOP}
