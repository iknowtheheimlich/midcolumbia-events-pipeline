"""Append-only classification review feedback and error-pattern analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class ReviewFeedback:
    feedback_id: str
    event_id: str
    title: str
    original_category: str | None
    corrected_category: str
    category_confidence: float
    category_reason: str
    category_evidence: list[dict[str, Any]]
    venue: str | None
    organizer: str | None
    source: str | None
    reviewer: str
    reviewed_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_feedback(
    event: dict[str, Any],
    corrected_category: str,
    *,
    reviewer: str = "human",
    reviewed_at: str | None = None,
) -> ReviewFeedback:
    corrected = _text(corrected_category)
    if not corrected:
        raise ValueError("corrected_category is required")
    event_id = _text(event.get("event_id") or event.get("dedupe_key") or event.get("legacy_dedupe_key"))
    if not event_id:
        seed = "|".join(
            (
                _text(event.get("source")) or "unknown",
                _text(event.get("title")) or "",
                _text(event.get("start_date") or event.get("date")) or "",
                _text(event.get("venue")) or "",
            )
        )
        event_id = "derived|" + sha256(seed.encode("utf-8")).hexdigest()[:24]
    timestamp = reviewed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    original = _text(event.get("category"))
    feedback_seed = f"{event_id}|{original}|{corrected}|{timestamp}"
    evidence = event.get("category_evidence")
    if not isinstance(evidence, list):
        evidence = []
    return ReviewFeedback(
        feedback_id=sha256(feedback_seed.encode("utf-8")).hexdigest()[:24],
        event_id=event_id,
        title=_text(event.get("title")) or "",
        original_category=original,
        corrected_category=corrected,
        category_confidence=float(event.get("category_confidence") or 0.0),
        category_reason=_text(event.get("category_reason")) or "",
        category_evidence=[item for item in evidence if isinstance(item, dict)],
        venue=_text(event.get("canonical_venue") or event.get("venue_registry_name") or event.get("venue")),
        organizer=_text(event.get("canonical_organizer") or event.get("organizer_registry_name") or event.get("organization") or event.get("organizer") or event.get("host")),
        source=_text(event.get("source")),
        reviewer=_text(reviewer) or "human",
        reviewed_at=timestamp,
    )


def load_feedback(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Expected object at {path}:{line_number}")
        rows.append(value)
    return rows


def append_feedback(path: Path, feedback: ReviewFeedback) -> bool:
    existing = load_feedback(path)
    if any(row.get("feedback_id") == feedback.feedback_id for row in existing):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(feedback.to_dict(), sort_keys=True, ensure_ascii=False) + "\n")
    return True


def analyze_feedback(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = list(rows)
    transitions = Counter()
    reasons = Counter()
    sources = Counter()
    venues = Counter()
    organizers = Counter()
    confidence_bands = Counter()
    unchanged = 0
    for row in records:
        original = _text(row.get("original_category"))
        corrected = _text(row.get("corrected_category"))
        if original == corrected:
            unchanged += 1
            continue
        transitions[f"{original or 'None'} -> {corrected or 'None'}"] += 1
        reason = _text(row.get("category_reason"))
        if reason:
            reasons[reason.split(";", 1)[0]] += 1
        source = _text(row.get("source"))
        if source:
            sources[source] += 1
        venue = _text(row.get("venue"))
        if venue:
            venues[venue] += 1
        organizer = _text(row.get("organizer"))
        if organizer:
            organizers[organizer] += 1
        confidence = float(row.get("category_confidence") or 0.0)
        confidence_bands[_confidence_band(confidence)] += 1
    corrected_count = len(records) - unchanged
    return {
        "reviews": len(records),
        "accepted_without_change": unchanged,
        "corrected": corrected_count,
        "override_rate": corrected_count / len(records) if records else 0.0,
        "top_transitions": transitions.most_common(10),
        "top_reasons": reasons.most_common(10),
        "top_sources": sources.most_common(10),
        "top_venues": venues.most_common(10),
        "top_organizers": organizers.most_common(10),
        "confidence_bands": dict(sorted(confidence_bands.items())),
    }


def render_feedback_report(summary: dict[str, Any]) -> str:
    lines = [
        "Attempt 81 Classification Review Feedback",
        "============================================",
        "",
        f"Reviews: {summary['reviews']}",
        f"Accepted without change: {summary['accepted_without_change']}",
        f"Corrected: {summary['corrected']}",
        f"Override rate: {summary['override_rate']:.1%}",
        "",
    ]
    sections = (
        ("TOP CATEGORY TRANSITIONS", "top_transitions"),
        ("TOP DECISION REASONS", "top_reasons"),
        ("TOP SOURCES", "top_sources"),
        ("TOP VENUES", "top_venues"),
        ("TOP ORGANIZERS", "top_organizers"),
    )
    for title, key in sections:
        lines.extend([title, "-" * len(title)])
        values = summary[key]
        if not values:
            lines.append("None")
        else:
            lines.extend(f"{label}: {count}" for label, count in values)
        lines.append("")
    lines.extend(["CONFIDENCE BANDS", "----------------"])
    if not summary["confidence_bands"]:
        lines.append("None")
    else:
        lines.extend(f"{label}: {count}" for label, count in summary["confidence_bands"].items())
    return "\n".join(lines).rstrip() + "\n"


def _confidence_band(value: float) -> str:
    if value >= 0.90:
        return "high"
    if value >= 0.75:
        return "medium"
    return "low"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
