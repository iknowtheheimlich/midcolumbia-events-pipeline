# Mid-Columbia Events Pipeline

A local-first event intelligence and publishing pipeline for Mid-Columbia community events. It harvests multiple sources, normalizes events into a canonical schema, resolves venues and organizers, deduplicates occurrences, classifies categories with explainable precedence, preserves human review history, and produces publisher-ready output plus operational health artifacts.

## Release Status

The pipeline is preparing for **v1.0.0-rc1** after Attempt 98.

Current regression baseline:

```text
430 tests passing
```

The current system includes:

- multi-source adapter framework
- canonical event schema and source attribution
- venue and organizer registries
- conservative occurrence resolution and deduplication
- explainable category intelligence
- venue and organizer category priors
- classified-history corpus and snapshots
- knowledge-drift detection
- human classification-review import/export
- review backlog aging, SLA, throughput, and capacity monitoring
- typed review-operations configuration
- unified weekly operational dashboard
- Reddit publishing and editorial formatting contracts

## Canonical Weekly Run

From the repository root:

```powershell
python -m pytest
python -m tools.finalize_weekly_run fixtures/real_multi_source/deduplicated_publisher_ready_events.json
```

A successful release-candidate run must complete the full test suite and generate the weekly operational artifacts without blocking failures.

## Primary Weekly Artifacts

The finalizer updates durable history and writes operational artifacts including:

```text
history/classified_events.jsonl
history/classification_reviews.jsonl
history/review_backlog.json
history/review_backlog_throughput.jsonl
history/snapshots/

artifacts/corpus_health.json
artifacts/corpus_health_report.txt
artifacts/review_operations_config.json
artifacts/review_operational_metrics.json
artifacts/review_backlog_report.txt
artifacts/review_sla_report.txt
artifacts/review_backlog_throughput_report.txt
artifacts/review_capacity_report.txt
artifacts/classification_review_batch.csv
artifacts/weekly_pipeline_health.json
artifacts/weekly_pipeline_health.txt
```

The first operator-facing file to inspect is:

```text
artifacts/weekly_pipeline_health.txt
```

Dashboard states are deliberately simple:

- `HEALTHY` — no current operational warnings
- `ATTENTION` — review debt or capacity requires action
- `DEGRADED` — report failures or corpus-integrity problems require investigation

The dashboard summarizes existing metrics; it does not replace the underlying reports.

## Review Workflow

The weekly finalizer exports:

```text
artifacts/classification_review_batch.csv
```

Reviewed decisions are imported into the durable review ledger. Already-reviewed event/category decisions are suppressed from future batches unless the classifier decision changes.

Review intelligence includes:

- new, recurring, and stale backlog states
- due-soon and overdue SLA states
- opened, carried, resolved, and net-change throughput
- capacity status and estimated time to clear
- immutable operational metric snapshots

## Category Decision Precedence

Category decisions follow the established precedence chain:

1. explicit title rules
2. existing or source category
3. venue or organizer registry hint
4. venue-type intelligence
5. description evidence
6. review queue

Registry hints are priors. They never override stronger evidence.

## Configuration

Review policy is represented by the typed `ReviewOperationsConfig` model and may be supplied through a JSON file:

```powershell
python -m tools.finalize_weekly_run <events.json> --review-config config/review_operations.json
```

Precedence is:

```text
built-in defaults < configuration file/object < explicit command-line overrides
```

The exact effective configuration used by each run is persisted to:

```text
artifacts/review_operations_config.json
```

## Useful Commands

Run the complete regression suite:

```powershell
python -m pytest
```

Run the status command:

```powershell
python -m tools.status
```

Inspect venue-intelligence candidates:

```powershell
python -m tools.report_venue_intelligence history/classified_events.jsonl
```

Inspect knowledge drift:

```powershell
python -m tools.report_knowledge_drift history/classified_events.jsonl
```

Inspect review backlog:

```powershell
python -m tools.report_review_backlog history/classified_events.jsonl
```

Inspect review capacity:

```powershell
python -m tools.report_review_capacity
```

## Architecture Contracts

The project relies on several non-negotiable contracts:

- source adapters normalize into a shared event model
- deduplication remains conservative and preserves attribution
- stronger category evidence outranks registry priors
- analytical reports do not silently alter decisions
- human review history is durable and idempotent
- weekly operational metrics must agree on active backlog
- configuration is validated rather than silently rewritten
- publisher output remains separate from review and recurrence queues

## Documentation

- [`docs/Architecture.md`](docs/Architecture.md)
- [`docs/EventSchema.md`](docs/EventSchema.md)
- [`docs/SourceAdapters.md`](docs/SourceAdapters.md)
- [`docs/VenueRegistry.md`](docs/VenueRegistry.md)
- [`docs/ResolverPipeline.md`](docs/ResolverPipeline.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)
- [`CHANGELOG.md`](CHANGELOG.md)

Historical attempt documents remain in `docs/attempts/` as implementation records. The README and release checklist define the current operational contract.

## Development Rule

Changes should preserve backward compatibility where practical and must end with a green full regression suite. New behavior requires a focused contract test; refactors must prove that existing observable behavior remains intact.
