"""Generic Algolia HTTP client utilities."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 30


def fetch_multi_query(
    *,
    url: str,
    app_id: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST a multi-query payload to Algolia and return decoded JSON.

    Uses Python standard library only so the pipeline does not gain a requests
    dependency just for one small POST.
    """
    if not url:
        raise ValueError("url is required")
    if not app_id:
        raise ValueError("app_id is required")
    if not api_key:
        raise ValueError("api_key is required")

    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url=url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Algolia-Application-Id": app_id,
            "X-Algolia-API-Key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"Algolia HTTP error {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Algolia request failed: {exc.reason}") from exc

    try:
        decoded = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Algolia response was not valid JSON") from exc

    if not isinstance(decoded, dict):
        raise RuntimeError("Algolia response was not a JSON object")

    return decoded
