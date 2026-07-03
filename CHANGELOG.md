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
- Added GitHub issues for roadmap milestones Attempt_14 through Attempt_21.
- Added `Attempt_20_Regression_Test_Suite` as a required milestone before production release.
- Renumbered production release planning from `Attempt_20_Production_Release` to `Attempt_21_Production_Release`.

### Notes

- Attempt_14 documentation now treats the Registry Optimizer, Venue Registry, Resolver Pipeline, Source Adapter boundary, and Event Schema as formal system contracts.
- Runtime verification of Registry Optimizer output still needs to be completed locally before starting `Attempt_15_Visit_Tri-Cities`.
- Production release now requires regression coverage before tagging/release.

## Attempt_21_Production_Release

### Planned

- First production release after regression suite passes.

## Attempt_20_Regression_Test_Suite

### Planned

- Known-good fixtures.
- Regression runner.
- Reddit output comparison.
- Notion export mapping comparison.
- Venue resolution coverage.
- Unknown venue queue coverage.
- Deduplication coverage.

## Attempt_19_Notion_Export

### Planned

- Notion export target using the canonical event schema.

## Attempt_18_Mid-Columbia_Libraries

### Planned

- Mid-Columbia Libraries source adapter.

## Attempt_17_Richland_Library

### Planned

- Richland Library source adapter.

## Attempt_16_Multi-Source_Deduplication

### Planned

- Shared deduplication stage across source adapters.

## Attempt_15_Visit_Tri-Cities

### Planned

- Visit Tri-Cities source adapter.

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
