# Attempt_52_ReviewTrainer

## Objective

Convert weekly editorial review items into deterministic, reusable human-feedback records without allowing generated output to rewrite classifier policy.

## Generated artifact

The live publisher writes:

```text
artifacts/review/Review_Training.json
```

Each record includes:

- stable fingerprint
- canonical event identity
- source and source event ID
- date, time, venue, and city
- current category decision and confidence
- geographic scope
- editorial review reason
- complete explainable-intelligence payload
- optional human correction

The fingerprint is derived from canonical identity fields rather than queue position, so corrections remain attached when sorting and review counts change.

## Curated corrections

Corrections are optional JSON input:

```json
{
  "corrections": [
    {
      "fingerprint": "0123456789abcdef",
      "action": "CATEGORY",
      "correct_category": "Food & Drink",
      "note": "Winemaker tasting event, not live music"
    }
  ]
}
```

Supported actions:

- `CATEGORY`
- `GEOGRAPHY`
- `SUPPRESS`
- `ACCEPT_REVIEW`

Use with:

```powershell
.\run_publish_reddit_live.bat 2026-07-12 --review-corrections config\review_corrections.json
```

Generated training artifacts remain outside tracked fixtures. Curated corrections are never generated or overwritten.

## Boundary

The trainer records decisions but does not automatically mutate category, geography, or publication rules. Accepted corrections should be promoted deliberately into focused classifier rules and regression tests.

Syndicated source records remain visible through occurrence provenance but do not count as independent corroborating authorities.
