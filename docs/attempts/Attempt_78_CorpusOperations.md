# Attempt 78 — Corpus Operations

## Goal

Make the classified-event corpus a normal post-run output instead of a manual maintenance step.

## Weekly command

```powershell
python -m tools.finalize_weekly_run <final-classified-events.json>
```

The finalizer:

1. Loads the final classified artifact.
2. Upserts eligible events into `history/classified_events.jsonl`.
3. Writes `artifacts/corpus_health.json`.
4. Writes `artifacts/corpus_health_report.txt`.
5. Runs venue-intelligence discovery and knowledge-drift reports against the updated corpus.

Report failures are non-blocking. A failed analytical report does not roll back or corrupt the corpus update.

## Health metrics

- total corpus events
- distinct sources
- distinct categories
- distinct venues
- distinct organizers
- missing venue/date/source counts
- category distribution
- source distribution

## Operating rule

Run the finalizer only after classification and publishing artifacts have completed successfully. Re-running the same weekly artifact is safe because the corpus uses correction-aware upsert semantics.
