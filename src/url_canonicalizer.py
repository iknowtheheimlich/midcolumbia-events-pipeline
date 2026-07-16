"""Normalize public destination URLs without hiding their domains."""

from __future__ import annotations

from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "si",
    "ref",
    "ref_src",
    "source",
}
_TRACKING_PREFIXES = ("utm_",)
_HOST_ALIASES = {
    "facebook.com": "www.facebook.com",
    "m.facebook.com": "www.facebook.com",
    "instagram.com": "www.instagram.com",
    "youtube.com": "www.youtube.com",
}


def canonicalize_url(value: str | None) -> str | None:
    """Return a stable direct URL, stripping tracking noise and fragments."""
    text = str(value or "").strip()
    if not text:
        return None
    if "://" not in text:
        text = f"https://{text}"

    parsed = urlsplit(text)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        return None

    host = parsed.hostname.casefold()
    host = _HOST_ALIASES.get(host, host)
    port = parsed.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_pairs = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_key(key)
    ]
    query = urlencode(sorted(query_pairs))
    return urlunsplit(("https", netloc, path, query, ""))


def canonicalize_urls(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        normalized = canonicalize_url(value)
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)


def _is_tracking_key(key: str) -> bool:
    lowered = key.casefold()
    return lowered in _TRACKING_KEYS or lowered.startswith(_TRACKING_PREFIXES)
