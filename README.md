# Mid-Columbia Events Pipeline

A local event harvesting, normalization, venue-resolution, and publishing pipeline for Mid-Columbia community event posts.

## Current Status

The current foundation is stable through:

```text
Attempt_16_Unified_Pipeline
```

Core capabilities documented so far:

- Cargo Harvester using saved HTML
- Stable canonical event schema
- Venue Registry with approximately 1,056 venues and Google Place IDs
- Registry Optimizer lookup generation
- Resolver Pipeline with Unknown Venue Queue routing
- Reddit Publisher chronological output
- Visit Tri-Cities Algolia-backed adapter
- Recurrence classification and publisher safety split
- Legacy CSV importer for old `unified_events.csv`
- Unified pipeline spine accepting multiple normalized source batches

## Verified Smoke Tests

Visit Tri-Cities fixture through unified pipeline:

```text
all_events: 24
publisher_ready_events: 15
recurrence_review_events: 9
```

Visit Tri-Cities plus legacy unified CSV through unified pipeline:

```text
all_events: 111
publisher_ready_events: 102
recurrence_review_events: 9
```

## Project Roadmap

See:

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`CHANGELOG.md`](CHANGELOG.md)

## Architecture Documents

- [`docs/Architecture.md`](docs/Architecture.md) — component boundaries and pipeline shape
- [`docs/EventSchema.md`](docs/EventSchema.md) — canonical event object contract
- [`docs/SourceAdapters.md`](docs/SourceAdapters.md) — adapter contract for adding new event sources
- [`docs/VenueRegistry.md`](docs/VenueRegistry.md) — canonical venue system
- [`docs/ResolverPipeline.md`](docs/ResolverPipeline.md) — venue resolution decision tree
- [`docs/Attempt_14_RegistryOptimizerVerification.md`](docs/Attempt_14_RegistryOptimizerVerification.md) — local verification checklist before Attempt_15
- [`docs/Attempt_15_VisitTriCities_SourceStrategy.md`](docs/Attempt_15_VisitTriCities_SourceStrategy.md) — Visit Tri-Cities source strategy

## GitHub Roadmap Issues

Current execution chain:

```text
#6   Attempt_14_Lock_Registry_Optimizer
  ↓
#7   Attempt_15_Visit_Tri-Cities
  ↓
#15  Attempt_16_Unified_Pipeline
  ↓
#8   Attempt_17_Multi-Source_Deduplication
  ↓
#9   Attempt_18_Richland_Library
  ↓
#10  Attempt_19_Mid-Columbia_Libraries
  ↓
#11  Attempt_20_Notion_Export
  ↓
#13  Attempt_21_Regression_Test_Suite
  ↓
#12  Attempt_22_Production_Release
```

## Development Rule

Every milestone uses this naming format:

```text
Attempt_##_<Description>
```

The event schema should remain backwards compatible whenever possible.

## Next Planned Milestone

```text
Attempt_17_Multi-Source_Deduplication
```

Before starting broad source expansion, keep the unified pipeline source-agnostic and preserve review queues separately from publisher-ready output.

Production release is gated by the regression test suite.
