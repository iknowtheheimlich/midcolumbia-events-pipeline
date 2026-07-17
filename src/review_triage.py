"""Operational triage for publisher review records.

This module does not change editorial disposition or launch policy. It adds an
explicit operational classification so Mission Control can distinguish expected
human classification work from records that are unsafe to publish as presented.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Iterable

EDITORIAL_REASONS = {"missing_or_unknown_category"}
ENTITY_BY_REASON = {
    "missing_or_unknown_category": "CATEGORY",
    "geographic_review": "GEOGRAPHY",
    "missing_city": "GEOGRAPHY",
    "unknown_geographic_scope": "GEOGRAPHY",
}


@dataclass(frozen=True)
class ReviewTriageRecord:
    fingerprint: str
    title: str
    source: str
    start_date: str
    venue: str
    city: str
    publication_url: str
    reason: str
    severity: str
    entity_type: str
    current_category: str | None = None
    category_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_review_record(record: dict[str, Any]) -> ReviewTriageRecord:
    reason = _text(record.get("editorial_reason")) or "unspecified_review"
    severity = "EDITORIAL_REVIEW" if reason in EDITORIAL_REASONS else "PUBLICATION_BLOCKER"
    entity_type = ENTITY_BY_REASON.get(reason, "PRESENTATION")
    return ReviewTriageRecord(
        fingerprint=_text(record.get("fingerprint")),
        title=_text(record.get("title")),
        source=_text(record.get("source")) or "Unknown",
        start_date=_text(record.get("start_date")),
        venue=_text(record.get("venue")),
        city=_text(record.get("city")),
        publication_url=_text(record.get("publication_url")),
        reason=reason,
        severity=severity,
        entity_type=entity_type,
        current_category=_optional_text(record.get("current_category")),
        category_reason=_optional_text(record.get("category_reason")),
    )


def build_review_triage(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    triaged = [classify_review_record(record) for record in records]
    return {
        "schema_version": 1,
        "record_count": len(triaged),
        "publication_blockers": sum(item.severity == "PUBLICATION_BLOCKER" for item in triaged),
        "editorial_reviews": sum(item.severity == "EDITORIAL_REVIEW" for item in triaged),
        "by_reason": dict(sorted(Counter(item.reason for item in triaged).items())),
        "by_entity_type": dict(sorted(Counter(item.entity_type for item in triaged).items())),
        "by_source": dict(sorted(Counter(item.source for item in triaged).items())),
        "records": [item.to_dict() for item in triaged],
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None
