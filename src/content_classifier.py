"""Deterministic screening for obvious non-event content.

Attempt_28_ProductionPolish

The classifier is intentionally conservative. Only strong navigation, account,
policy, employment, and pagination titles are rejected automatically. Everything
else remains an event or review candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable


_SPACE_RE = re.compile(r"\s+")
_PAGE_NUMBER_RE = re.compile(r"^page\s+\d+$", re.IGNORECASE)
_CURRENT_PAGE_RE = re.compile(r"^current\s+page\s+\d+$", re.IGNORECASE)

NAVIGATION_TITLES = {
    "next page",
    "next page ››",
    "previous page",
    "previous page ‹‹",
    "home",
    "calendar",
}

ACCOUNT_TITLES = {
    "login",
    "log in",
    "sign in",
    "intranet",
    "my account",
}

DOCUMENT_TITLES = {
    "all library policies",
    "privacy policy",
    "terms of use",
}

JOB_TITLES = {
    "employment opportunities",
    "careers",
    "jobs",
}

ADMIN_TITLES = {
    "volunteer",
}


@dataclass(frozen=True)
class ContentClassification:
    kind: str
    publishable: bool
    reason: str | None = None


def normalize_title(value: str | None) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip()).casefold()


def classify_content(event: dict[str, Any]) -> ContentClassification:
    """Classify one normalized item without guessing about ordinary titles."""
    title = normalize_title(event.get("title"))
    if not title:
        return ContentClassification("UNKNOWN", False, "missing_title")

    if _PAGE_NUMBER_RE.fullmatch(title) or _CURRENT_PAGE_RE.fullmatch(title):
        return ContentClassification("NAVIGATION", False, "pagination_title")
    if title in NAVIGATION_TITLES:
        return ContentClassification("NAVIGATION", False, "navigation_title")
    if title in ACCOUNT_TITLES:
        return ContentClassification("PAGE", False, "account_page")
    if title in DOCUMENT_TITLES:
        return ContentClassification("DOCUMENT", False, "document_page")
    if title in JOB_TITLES:
        return ContentClassification("JOB", False, "employment_page")
    if title in ADMIN_TITLES:
        return ContentClassification("PAGE", False, "administrative_page")

    return ContentClassification("EVENT", True)


def screen_events(events: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return publishable items and rejected items annotated with audit fields."""
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for event in events:
        copied = dict(event)
        classification = classify_content(copied)
        copied["content_kind"] = classification.kind
        if classification.publishable:
            accepted.append(copied)
        else:
            copied["content_rejection_reason"] = classification.reason
            rejected.append(copied)

    return accepted, rejected
