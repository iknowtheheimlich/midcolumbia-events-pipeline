# Attempt 98 — Operational Dashboard

## Goal

Provide one weekly operator-facing health artifact assembled from metrics already computed by the pipeline.

## Outputs

- `artifacts/weekly_pipeline_health.txt`
- `artifacts/weekly_pipeline_health.json`

## Status rules

- `degraded`: analytical report failures or corpus events missing source/date
- `attention`: overdue/stale review work, over-capacity review flow, or missing venue
- `healthy`: no operational exceptions detected

The status is rule-based and explainable. It is not a weighted score.

## Boundaries

- Existing reports remain available.
- Existing calculations remain authoritative.
- No classification, confidence, review, or publishing behavior changes.
- The dashboard is generated after the analytical report pass so current-run failures are represented.

## Validation

```powershell
python -m pytest tests/test_operational_dashboard.py
python -m pytest
python -m tools.finalize_weekly_run fixtures/real_multi_source/deduplicated_publisher_ready_events.json
```
