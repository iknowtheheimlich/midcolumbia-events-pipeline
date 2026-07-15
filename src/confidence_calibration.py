"""Compare classifier confidence against human review outcomes without mutating scores."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Iterable


@dataclass(frozen=True)
class CalibrationBand:
    band: str
    reviews: int
    accepted: int
    corrected: int
    mean_confidence: float
    observed_accuracy: float
    calibration_gap: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def confidence_band(value: float) -> str:
    if value >= 0.90:
        return "high"
    if value >= 0.75:
        return "medium"
    return "low"


def calibration_status(gap: float, reviews: int, *, min_reviews: int = 10) -> str:
    if reviews < min_reviews:
        return "insufficient"
    if gap > 0.10:
        return "overconfident"
    if gap < -0.10:
        return "underconfident"
    return "calibrated"


def analyze_calibration(
    rows: Iterable[dict[str, Any]], *, min_reviews: int = 10
) -> dict[str, Any]:
    records = list(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    squared_errors: list[float] = []

    for row in records:
        confidence = _confidence(row.get("category_confidence"))
        outcome = 1.0 if _text(row.get("original_category")) == _text(row.get("corrected_category")) else 0.0
        grouped[confidence_band(confidence)].append({"confidence": confidence, "outcome": outcome})
        squared_errors.append((confidence - outcome) ** 2)

    bands: list[CalibrationBand] = []
    for band in ("low", "medium", "high"):
        items = grouped.get(band, [])
        reviews = len(items)
        accepted = sum(int(item["outcome"]) for item in items)
        corrected = reviews - accepted
        mean_confidence = sum(item["confidence"] for item in items) / reviews if reviews else 0.0
        observed_accuracy = accepted / reviews if reviews else 0.0
        gap = mean_confidence - observed_accuracy if reviews else 0.0
        bands.append(
            CalibrationBand(
                band=band,
                reviews=reviews,
                accepted=accepted,
                corrected=corrected,
                mean_confidence=mean_confidence,
                observed_accuracy=observed_accuracy,
                calibration_gap=gap,
                status=calibration_status(gap, reviews, min_reviews=min_reviews),
            )
        )

    accepted_total = sum(
        1 for row in records if _text(row.get("original_category")) == _text(row.get("corrected_category"))
    )
    mean_confidence = (
        sum(_confidence(row.get("category_confidence")) for row in records) / len(records)
        if records
        else 0.0
    )
    observed_accuracy = accepted_total / len(records) if records else 0.0
    overall_gap = mean_confidence - observed_accuracy if records else 0.0

    return {
        "reviews": len(records),
        "accepted": accepted_total,
        "corrected": len(records) - accepted_total,
        "mean_confidence": mean_confidence,
        "observed_accuracy": observed_accuracy,
        "calibration_gap": overall_gap,
        "brier_score": sum(squared_errors) / len(squared_errors) if squared_errors else 0.0,
        "status": calibration_status(overall_gap, len(records), min_reviews=min_reviews),
        "minimum_reviews_per_band": min_reviews,
        "bands": [band.to_dict() for band in bands],
    }


def render_calibration_report(summary: dict[str, Any]) -> str:
    lines = [
        "Attempt 82 Confidence Calibration",
        "=================================",
        "",
        f"Reviews: {summary['reviews']}",
        f"Accepted: {summary['accepted']}",
        f"Corrected: {summary['corrected']}",
        f"Mean confidence: {summary['mean_confidence']:.1%}",
        f"Observed accuracy: {summary['observed_accuracy']:.1%}",
        f"Calibration gap: {summary['calibration_gap']:+.1%}",
        f"Brier score: {summary['brier_score']:.3f}",
        f"Status: {summary['status']}",
        "",
        "BY CONFIDENCE BAND",
        "------------------",
    ]
    for band in summary["bands"]:
        lines.extend(
            [
                "",
                band["band"].upper(),
                f"  Reviews: {band['reviews']}",
                f"  Accepted: {band['accepted']}",
                f"  Corrected: {band['corrected']}",
                f"  Mean confidence: {band['mean_confidence']:.1%}",
                f"  Observed accuracy: {band['observed_accuracy']:.1%}",
                f"  Calibration gap: {band['calibration_gap']:+.1%}",
                f"  Status: {band['status']}",
            ]
        )
    if not summary["reviews"]:
        lines.extend(
            [
                "",
                "No human review outcomes are available yet. Calibration begins once the review ledger contains accepted and corrected decisions.",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _confidence(value: Any) -> float:
    try:
        return min(1.0, max(0.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
