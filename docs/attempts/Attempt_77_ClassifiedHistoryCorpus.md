# Attempt 77 — Classified History Corpus

## Goal

Create a durable historical input for venue discovery and knowledge drift analysis.

Weekly pipeline outputs are snapshots. Attempts 74 and 76 require accumulated final classifications across many runs. Attempt 77 stores those final events in a deterministic JSONL corpus.

## Contract

- Corpus path: `history/classified_events.jsonl`
- Only events with a final `category` are retained.
- Repeated runs upsert by stable event identity.
- Corrected classifications replace older versions of the same event.
- Unclassified/raw collection rows are skipped.
- Output ordering and JSON keys are deterministic for useful Git diffs.

## Identity precedence

1. `event_id`
2. `legacy_dedupe_key`
3. `dedupe_key`
4. `source + url`
5. derived hash of source, title, date, and canonical venue

## Weekly operation

After the final classified publisher-ready artifact exists:

```powershell
python -m tools.update_classified_history <classified-events.json>
```

Then venue discovery and drift analysis can use the accumulated corpus:

```powershell
python -m tools.report_venue_intelligence history/classified_events.jsonl
python -m tools.report_knowledge_drift history/classified_events.jsonl
```

The history corpus is operational data. Commit it only when the project intentionally wants the repository itself to carry the archive; otherwise keep the same format in a backed-up local data directory.

## Non-goals

- No automatic classification of raw history.
- No database dependency.
- No destructive pruning.
- No automatic venue or organizer hint changes.
