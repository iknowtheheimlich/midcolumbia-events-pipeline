# Attempt_46_TimeSemantics

## Objective

Remove transport-layer clock sentinels before publisher projection and represent all-day events explicitly.

## Contract

The enrichment is opt-in:

```python
run_pipeline(..., enrich_time_semantics=True)
```

Production enables it. Existing callers retain prior behavior unless they opt in.

## Rules

- Explicit all-day or date-only markers become `all_day=True` and display as `All day`.
- Legacy AllEvents records coerced to midnight are repaired as all-day when no real end time exists.
- Same-day midnight-to-midnight records become all-day.
- `23:59` end times are treated as synthetic unknown-end sentinels and removed.
- End times identical to start times are removed.
- Legitimate midnight starts with a later real end time remain midnight.

## Explainability

Each enriched event records:

```text
intelligence.time_semantics.value
intelligence.time_semantics.confidence
intelligence.time_semantics.reason
```

## Boundaries

- No collector-specific publisher code.
- No category or occurrence-resolution changes.
- No generated artifacts stored with fixtures.
