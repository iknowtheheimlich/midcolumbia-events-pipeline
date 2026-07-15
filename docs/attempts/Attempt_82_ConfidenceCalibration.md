# Attempt 82 — Confidence Calibration

## Goal

Measure whether classification confidence corresponds to human review outcomes.

This attempt is observational. It does not modify category decisions, rule weights, confidence values, venue hints, or organizer hints.

## Inputs

`history/classification_reviews.jsonl` from Attempt 81.

A review is treated as correct when `original_category == corrected_category` and incorrect when the reviewer changes the category.

## Metrics

- total reviewed decisions
- accepted and corrected counts
- observed accuracy
- mean stated confidence
- calibration gap (`mean confidence - observed accuracy`)
- Brier score
- per-band metrics for low, medium, and high confidence

## Status rules

Each band requires at least 10 reviews by default.

- `insufficient`: below the minimum sample
- `overconfident`: confidence exceeds observed accuracy by more than 10 percentage points
- `underconfident`: observed accuracy exceeds confidence by more than 10 percentage points
- `calibrated`: gap remains within ±10 percentage points

## Run

```powershell
python -m tools.report_confidence_calibration
```

Optional outputs:

```powershell
python -m tools.report_confidence_calibration `
  --json artifacts/confidence_calibration.json `
  --output artifacts/confidence_calibration_report.txt
```

An empty review ledger should produce a valid `insufficient` report rather than an error.
