# Attempt 79 — Corpus Snapshots and Restore

## Goal

Protect the classified history corpus from accidental destructive updates without adding a database or changing the JSONL contract.

## Behavior

`tools.finalize_weekly_run` now snapshots the current non-empty corpus immediately before writing the merged weekly state.

Snapshots are stored under:

```text
history/snapshots/
```

Names contain a UTC timestamp and checksum prefix:

```text
classified_events_20260715T123000Z_a1b2c3d4e5f6.jsonl
```

An empty initial corpus creates no meaningless snapshot.

## Restore

```powershell
python -m tools.restore_classified_history history/snapshots/<snapshot>.jsonl
```

The restore command validates JSONL input, replaces the active corpus, and prints the restored event count and checksum.

## Safety contract

- Snapshot occurs before corpus mutation.
- Snapshot creation is deterministic and local.
- Restore is explicit; no automatic rollback occurs.
- Existing corpus and report behavior remain unchanged.
