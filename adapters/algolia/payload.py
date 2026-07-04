"""Generic Algolia payload utilities."""

from __future__ import annotations

from typing import Any


def extract_hits(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    """Extract Algolia-style hits from common response shapes.

    Supported shapes:
    - list[hit]
    - {"hits": [...]}
    - {"results": [{"hits": [...]}]}
    """
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict or list")

    if isinstance(payload.get("hits"), list):
        return [item for item in payload["hits"] if isinstance(item, dict)]

    results = payload.get("results")
    if isinstance(results, list):
        hits: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, dict) and isinstance(result.get("hits"), list):
                hits.extend(item for item in result["hits"] if isinstance(item, dict))
        return hits

    return []


def build_multi_query_payload(index_name: str, params: str) -> dict[str, list[dict[str, str]]]:
    """Build an Algolia multi-query payload."""
    if not index_name:
        raise ValueError("index_name is required")
    if not isinstance(params, str):
        raise TypeError("params must be a string")

    return {"requests": [{"indexName": index_name, "params": params}]}
