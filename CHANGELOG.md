# Changelog

All notable project changes should be recorded here.

Milestones use the required format:

```text
Attempt_##_<Description>
```

## Unreleased

### Added

- Added `docs/ROADMAP.md` as the canonical project history and milestone roadmap.
- Added `docs/Architecture.md` to define major pipeline boundaries.
- Added `docs/EventSchema.md` to document the stable canonical event schema.
- Added `docs/SourceAdapters.md` to define the adapter contract for future event sources.
- Added `docs/VenueRegistry.md` to document the canonical venue system.
- Added `docs/ResolverPipeline.md` to document venue resolution behavior.
- Added `docs/Attempt_14_RegistryOptimizerVerification.md` to define the verification checklist for locking Attempt_14.
- Added `docs/Attempt_15_VisitTriCities_SourceStrategy.md` to document the Visit Tri-Cities source strategy.
- Added GitHub issues for roadmap milestones Attempt_14 through Attempt_22.
- Added `Attempt_21_Regression_Test_Suite` as a required milestone before production release.
- Renumbered production release planning to `Attempt_22_Production_Release`.

### Notes

- Attempt_14 documentation now treats the Registry Optimizer, Venue Registry, Resolver Pipeline, Source Adapter boundary, and Event Schema as formal system contracts.
- Visit Tri-Cities proved the adapter architecture can support an API-backed source without changing the publisher or resolver.
- Production release requires regression coverage before tagging/release.

## Attempt_22_Production_Release

### Planned

- First production release after regression suite passes.

## Attempt_21_Regression_Test_Suite

### Planned

- Known-good fixtures.
- Regression runner.
- Reddit output comparison.
- Notion export mapping comparison.
- Venue resolution coverage.
- Unknown venue queue coverage.
- Deduplication coverage.

## Attempt_20_Notion_Export

### Planned

- Notion export target using the canonical event schema.

## Attempt_19_Mid-Columbia_Libraries

### Verified

- Mid-Columbia Libraries real fixture normalized 37 events.
- Four-source status run:
  - Input: 160
  - Publisher: 151
  - Deduplicated: 150
  - Series Review: 9
  - Duplicate Groups: 1
  - Low Quality Skips: 30
- Regression suite passes.

### Planned

- Mid-Columbia Libraries source adapter.

## Attempt_19_Status_Command

### Added

- Added `tools/status.py` as a compact project status command.
- Status command loads all registered adapters from `adapters/registry.py`.
- Status command reports adapter statuses, fixture counts, latest pipeline counts, review queue count, duplicate group count, and low-quality dedupe skips.

### Verified

- `python -m tools.status` reports:
  - `Input`: 123
  - `Publisher`: 114
  - `Deduplicated`: 113
  - `Series Review`: 9
  - `Duplicate Groups`: 1
  - `Low Quality Skips`: 30

## Attempt_18_Richland_Library

### Added

- Added Richland Library source strategy documentation.
- Added Richland Library adapter package scaffold.
- Added LibCal/Springshare request configuration and request builder.
- Added Richland Library HTML fragment parser.
- Added fixture workflow for Richland Library raw and normalized events.
- Added generic N-source pipeline runner: `tools/run_sources_pipeline.py`.
- Added adapter registry: `adapters/registry.py`.
- Added regression tests for Richland Library, deduplication, adapter registry, and three-source pipeline counts.
- Added `requirements-dev.txt` and `run_tests.bat` for repeatable local test runs.

### Verified

- Richland Library LibCal monthly fragment normalized 12 events.
- Richland Library alone through the pipeline:
  - `all_events`: 12
  - `publisher_ready_events`: 12
  - `recurrence_review_events`: 0
  - `deduplicated_publisher_ready_events`: 12
  - `duplicate_groups`: 0
  - `skipped_low_quality_dedupe`: 0
- Three-source run with Visit Tri-Cities + Legacy CSV + Richland Library:
  - `all_events`: 123
  - `publisher_ready_events`: 114
  - `deduplicated_publisher_ready_events`: 113
  - `duplicate_groups`: 1
  - `recurrence_review_events`: 9
  - `skipped_low_quality_dedupe`: 30
- Regression suite:
  - `8 passed`

## Attempt_17_Multi-Source_Deduplication

### Added

- Added `src/deduplicate.py` with conservative exact-key deduplication.
- Added low-quality key gating to prevent unsafe merges when legacy fields are sparse.
- Added `tools/deduplicate_real_multi_source.py` as a standalone dedupe smoke tool.
- Added deduplication into `src/pipeline.py` as an optional formal pipeline stage.
- Updated `tools/run_real_multi_source_pipeline.py` to write publisher-ready, deduplicated publisher-ready, dedupe report, and recurrence-review outputs.
- Added `tools/inspect_legacy_csv.py` to inspect legacy CSV headers and sample rows.
- Updated `tools/import_legacy_unified_events.py` to map Title Case legacy CSV columns into canonical event fields.

### Verified

- Initial unsafe dedupe test correctly exposed false grouping risk:
  - `input_events`: 102
  - `deduplicated_events`: 16
  - `duplicate_groups`: 1
  - `duplicate_events_removed`: 86
- After key-quality gating:
  - `input_events`: 102
  - `deduplicated_events`: 102
  - `duplicate_groups`: 0
  - `skipped_low_quality`: 87
- After legacy importer field mapping:
  - `input_events`: 102
  - `deduplicated_events`: 101
  - `duplicate_groups`: 1
  - `duplicate_events_removed`: 1
  - `skipped_low_quality`: 30
- Formal pipeline run with dedupe enabled:
  - `all_events`: 111
  - `publisher_ready_events`: 102
  - `deduplicated_publisher_ready_events`: 101
  - `duplicate_groups`: 1
  - `recurrence_review_events`: 9
  - `skipped_low_quality_dedupe`: 30

## Attempt_16_Unified_Pipeline

### Added

- Added `src/pipeline.py` as the unified source-agnostic pipeline spine.
- Added `SourceBatch` and `PipelineResult` contracts.
- Added `tools/run_visit_tricities_pipeline.py` for VTC pipeline smoke testing.
- Added `tools/run_multi_source_pipeline.py` for mock multi-source smoke testing.
- Added `tools/run_real_multi_source_pipeline.py` for VTC plus second-source pipeline runs.
- Added `tools/import_legacy_unified_events.py` to convert legacy `unified_events.csv` into canonical JSON.
- Added `fixtures/legacy/normalized_events.json` workflow as the bridge from old pipeline output into the new pipeline.

### Verified

- Visit Tri-Cities fixture pipeline run:
  - `all_events`: 24
  - `publisher_ready_events`: 15
  - `recurrence_review_events`: 9
- Visit Tri-Cities plus legacy unified CSV pipeline run:
  - `all_events`: 111
  - `publisher_ready_events`: 102
  - `recurrence_review_events`: 9

## Attempt_15_Visit_Tri-Cities

### Added

- Visit Tri-Cities adapter scaffold.
- Generic Algolia payload utilities.
- Generic Algolia client.
- Visit Tri-Cities Algolia config and request builder.
- Fixture fetch and normalization tools.
- Recurrence classification safety split.

### Verified

- VTC Algolia payload builder runs.
- VTC fixture fetch runs.
- VTC normalization writes 24 normalized events.
- Publisher safety split produces 15 publisher-ready events and 9 recurrence-review events after classifier tightening.

## Attempt_14_Registry_Optimizer

### Added

- Registry Optimizer milestone documented.
- Generated lookup table behavior documented.
- Venue Registry governance documented.
- Resolver decision tree documented.
- Attempt_14 lock criteria documented.

### Required Before Attempt_15

- Verify optimizer output is deterministic.
- Confirm resolver consumes generated lookup tables.
- Confirm known venues resolve correctly.
- Confirm unknown venues route cleanly to the review queue.
- Confirm Reddit Publisher output remains chronological.

## Attempt_13_Skeptical_Builder

### Added

- Skeptical venue-building approach established before optimizer work.

## Attempt_12_Venue_Builder

### Added

- Venue Builder milestone established for constructing Venue Registry entries.

## Attempt_11_Unknown_Venue_Queue

### Added

- Unknown venues separated into a dedicated review queue.

## Attempt_10_Indexed_Resolver

### Added

- Indexed venue resolution milestone established.

## Attempt_09_Master_Resolver

### Added

- Master resolver milestone established.

## Attempt_08_Venue_Resolver

### Added

- Venue Resolver milestone established.

## Attempt_07_Output_Contract

### Added

- Stable output contract milestone established.

## Attempt_06_Validation

### Added

- Validation milestone established.

## Attempt_05_Publisher

### Added

- Reddit Publisher milestone established.

## Attempt_04_Locality_Scoring

### Added

- Locality scoring milestone established.

## Attempt_03_URL_Parser

### Added

- URL Parser milestone established.

## Attempt_02_Saved_HTML

### Added

- Saved HTML workflow milestone established.

## Attempt_01_Foundation

### Added

- Initial foundation milestone established.
