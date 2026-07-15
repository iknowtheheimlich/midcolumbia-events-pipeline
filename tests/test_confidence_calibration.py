from src.confidence_calibration import analyze_calibration, calibration_status, render_calibration_report


def row(confidence: float, original: str, corrected: str) -> dict:
    return {
        "category_confidence": confidence,
        "original_category": original,
        "corrected_category": corrected,
    }


def test_empty_calibration_is_insufficient():
    summary = analyze_calibration([])
    assert summary["reviews"] == 0
    assert summary["status"] == "insufficient"
    assert "No human review outcomes" in render_calibration_report(summary)


def test_accepted_review_counts_as_correct_outcome():
    summary = analyze_calibration([row(0.95, "Sports", "Sports")], min_reviews=1)
    assert summary["accepted"] == 1
    assert summary["corrected"] == 0
    assert summary["observed_accuracy"] == 1.0


def test_corrected_review_counts_as_incorrect_outcome():
    summary = analyze_calibration([row(0.95, "Sports", "Music/Comedy")], min_reviews=1)
    assert summary["accepted"] == 0
    assert summary["corrected"] == 1
    assert summary["observed_accuracy"] == 0.0


def test_high_confidence_wrong_decisions_are_overconfident():
    summary = analyze_calibration(
        [row(0.95, "Sports", "Music/Comedy") for _ in range(10)], min_reviews=10
    )
    high = next(item for item in summary["bands"] if item["band"] == "high")
    assert high["status"] == "overconfident"
    assert high["calibration_gap"] == 0.95


def test_low_confidence_correct_decisions_are_underconfident():
    summary = analyze_calibration(
        [row(0.40, "Sports", "Sports") for _ in range(10)], min_reviews=10
    )
    low = next(item for item in summary["bands"] if item["band"] == "low")
    assert low["status"] == "underconfident"
    assert low["calibration_gap"] == -0.6


def test_band_requires_minimum_review_count():
    summary = analyze_calibration(
        [row(0.95, "Sports", "Music/Comedy") for _ in range(9)], min_reviews=10
    )
    high = next(item for item in summary["bands"] if item["band"] == "high")
    assert high["status"] == "insufficient"


def test_status_boundary_is_calibrated():
    assert calibration_status(0.10, 10) == "calibrated"
    assert calibration_status(-0.10, 10) == "calibrated"


def test_confidence_values_are_clamped():
    summary = analyze_calibration(
        [row(4.0, "Sports", "Sports"), row(-2.0, "Sports", "Music/Comedy")],
        min_reviews=1,
    )
    assert summary["mean_confidence"] == 0.5
