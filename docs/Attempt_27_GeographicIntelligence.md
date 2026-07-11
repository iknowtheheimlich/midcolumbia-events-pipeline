# Attempt_27 Geographic Intelligence

## Purpose

Add deterministic geographic classification without introducing a network geocoder or changing publisher behavior.

## Current capabilities

- Normalize city and state names.
- Recover city/state from common address formats.
- Classify events into geographic regions.
- Classify scope as `LOCAL`, `REGIONAL_REVIEW`, `OUT_OF_AREA`, or `REVIEW`.
- Calculate Haversine distances to Kennewick, Richland, and Pasco when coordinates already exist.
- Produce an audit report before any geographic filtering is enabled.

## Regions

- `TRI_CITIES`
- `LOWER_VALLEY`
- `WALLA_WALLA`
- `YAKIMA`
- `MOSES_LAKE`
- `COLUMBIA_GORGE`
- `PENDLETON`
- `SPOKANE`
- `OTHER`
- `UNKNOWN`

## Safety boundary

Geographic enrichment is optional in `run_pipeline(..., enrich_geography=True)`.
Attempt_27 does not delete or suppress events. The report identifies candidates for future filtering so locality policy can be reviewed against live data first.

## Report

```powershell
python -m tools.report_geographic_intelligence
```

Output:

```text
generated/geographic_intelligence/report.txt
```
