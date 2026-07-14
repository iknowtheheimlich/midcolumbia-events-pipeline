# Attempt_57_EventCompletenessIntelligence

## Objective

Measure publication-relevant event completeness and use it to choose the most informative record within conservative exact-duplicate groups.

## Behavior

- Scores weighted field presence across identity, location, descriptive, media, cost, schedule, registration, and end-time fields.
- Supports equivalent fields such as `venue_id` for venue and `external_url` for URL.
- Attaches optional explainable completeness intelligence when the pipeline enrichment flag is enabled.
- Produces `artifacts/reddit/Completeness_Audit.txt` for weekly events below 80% completeness.
- Routes the audit to degraded artifacts when harvest health blocks normal production.
- Uses completeness before source priority when selecting the canonical record in exact duplicate groups.
- Preserves all duplicate source and URL provenance.

## Compatibility

Completeness enrichment is opt-in at the shared pipeline boundary. Existing fixture-backed and legacy callers retain their established event shapes. The production audit can calculate scores directly from resolved events.

## Deliberate limits

This attempt does not perform field-by-field fusion across source records. A nonblank value is not automatically authoritative, and combining conflicting values without provenance policy would create synthetic records that no source actually published.

Cross-source occurrence identity remains governed by Occurrence Resolution. This attempt changes canonical selection only for conservative exact duplicate groups.

## Generated artifact

```text
artifacts/reddit/Completeness_Audit.txt
```

The report contains:

- weekly event count
- average completeness
- common missing fields
- events below the configured threshold
- missing fields and source URL for each low-completeness event
