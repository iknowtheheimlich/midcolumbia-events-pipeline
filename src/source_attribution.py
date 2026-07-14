"""Build deterministic public-source attribution for generated publications.

Attempt_55_DynamicPublicationAttribution
"""

from __future__ import annotations

from collections.abc import Iterable

from adapters.registry import AdapterInfo

DEFAULT_ATTRIBUTION_PREFIX = "This is not an all inclusive list. Events were extracted from"


def build_source_attribution(
    adapters: Iterable[AdapterInfo],
    *,
    prefix: str = DEFAULT_ATTRIBUTION_PREFIX,
) -> str:
    """Return a stable human-readable attribution for public source adapters."""
    labels = [
        adapter.attribution_label
        for adapter in adapters
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
