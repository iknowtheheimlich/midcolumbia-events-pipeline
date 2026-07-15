# Attempt 92 — Architecture Audit

## Scope

Audit the post-Attempt-91 system before adding more features. The goal is to reduce duplicate responsibility, inconsistent contracts, and configuration drift while preserving all existing behavior.

## Findings

### 1. Event input loading was duplicated

At least three modules independently parsed JSON and JSONL event artifacts:

- `tools/update_classified_history.py`
- `src/classification_review_batch.py`
- `tools/report_knowledge_drift.py`

They accepted different envelope keys and handled malformed JSONL differently. The same artifact could therefore be accepted by one tool and rejected by another.

Resolution in this attempt:

- add `src/event_io.py`
- centralize supported envelope keys
- centralize JSONL validation and line-number errors
- preserve existing loader names as compatibility aliases

### 2. Operational thresholds are distributed

Backlog aging, SLA thresholds, and capacity lookback are currently declared in the weekly finalizer and repeated in individual report CLIs.

Recommendation:

- centralize operational defaults in a typed configuration object
- keep CLI flags as overrides
- defer until loader consolidation is validated

### 3. Weekly finalization owns too many orchestration details

`tools/finalize_weekly_run.py` currently performs corpus updates, snapshots, health reporting, backlog reconciliation, SLA analysis, throughput analysis, capacity analysis, review export, and subprocess report execution.

Recommendation:

- extract a review-operations service returning one structured result
- leave the CLI responsible only for argument parsing and rendering
- do not split this until contract tests cover the current return schema

### 4. Reporting modules repeat storage concerns

Several report tools independently read JSONL history and write artifact paths. This is manageable now but will continue to diverge.

Recommendation:

- create shared JSONL record I/O after event loading is consolidated
- avoid a generic utility grab bag; use domain-named modules

### 5. Test count is healthy; contract quality needs monitoring

The suite has 399 tests. Recent failures show a smaller but important risk: some tests assert a narrative expectation rather than the mathematical or architectural contract.

Recommendation:

- retain behavior-focused unit tests
- prefer invariants and formula-derived expectations
- audit duplicate integration fixtures after the orchestration split

## Deferred work order

1. Validate canonical event loading.
2. Centralize operational configuration defaults.
3. Extract weekly review orchestration.
4. Consolidate generic JSONL record loading.
5. Audit redundant tests and fixtures.

## Non-goals

- no new classification intelligence
- no automatic learning
- no category changes
- no removal of public compatibility imports
