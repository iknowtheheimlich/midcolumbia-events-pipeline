"""Normalize public destination URLs without hiding their domains."""

from __future__ import annotations

import re
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
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_EMBEDDED_WEB_SCHEME_RE = re.compile(r"https?://", re.IGNORECASE)


def validate_public_http_url(value: str | None, *, field: str = "URL") -> str:
    """Validate a public HTTP(S) destination without changing its presentation."""
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is empty")
    if not text.casefold().startswith(("http://", "https://")):
        raise ValueError(f"{field} must use http:// or https://: {text!r}")
    if len(_EMBEDDED_WEB_SCHEME_RE.findall(text)) != 1:
        raise ValueError(f"{field} contains an embedded absolute URL: {text!r}")

    parsed = urlsplit(text)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{field} is not a valid HTTP(S) URL: {text!r}")
    if "." not in parsed.hostname:
        raise ValueError(f"{field} hostname is not a public domain: {parsed.hostname!r}")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError(f"{field} has an invalid port: {text!r}") from exc
    return text


def canonicalize_url(value: str | None) -> str | None:
    """Return a stable direct URL, stripping tracking noise and fragments."""
    text = str(value or "").strip()
    if not text:
        return None

    # Reject explicit non-web schemes before treating a value as a bare hostname.
    if _SCHEME_RE.match(text) and not text.casefold().startswith(("http://", "https://")):
        return None
    if "://" not in text:
        text = f"https://{text}"

    try:
        validate_public_http_url(text)
    except ValueError:
        return None

    parsed = urlsplit(text)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        return None

    host = parsed.hostname.casefold()
    host = _HOST_ALIASES.get(host, host)
    try:
        port = parsed.port
    except ValueError:
        return None
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
