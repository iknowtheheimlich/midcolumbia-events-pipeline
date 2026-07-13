# Attempt_44_PipelineInspector

## Objective

Provide a deterministic HTML trace of one event through the production Mid-Columbia Event Intelligence pipeline without changing classification or publication behavior.

## Operating command

```powershell
.\run_publish_reddit_live.bat 2026-07-12 --inspect-title "Summer Thursdays"
```

Default artifact:

```text
artifacts/inspector/Pipeline_Inspector.html
```

Custom path:

```powershell
.\run_publish_reddit_live.bat 2026-07-12 --inspect-title "Summer Thursdays" --output-inspector artifacts\inspector\summer_thursdays.html
```

## Included stages

- Collected normalized source records
- Normalized and enriched canonical events
- Publisher-ready occurrences
- Resolved occurrences
- Publisher projection
- Editorial projection
- Program projection
- Final Reddit lines

The search is case-insensitive and checks the complete JSON-safe stage record. A venue, source URL, source event ID, or intelligence reason may therefore be used when the title is not distinctive enough.

## Boundaries

- The inspector observes the production run; it does not re-run intelligence independently.
- No source-specific parsing exists in the inspector.
- No pipeline decision is modified by inspection.
- Generated HTML remains outside fixture directories.
- Output is deterministic for stable pipeline inputs.
