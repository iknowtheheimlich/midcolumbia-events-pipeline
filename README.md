# Mid-Columbia Events Pipeline

A local event harvesting, normalization, venue-resolution, deduplication, and publishing pipeline for Mid-Columbia community event posts.

## Current Status

The current foundation is stable through:

```text
Attempt_21_TriCityVibe
```

Core capabilities documented so far:

- Cargo Harvester using saved HTML
- Stable canonical event schema
- Venue Registry with approximately 1,056 venues and Google Place IDs
- Registry Optimizer lookup generation
- Resolver Pipeline with Unknown Venue Queue routing
- Reddit Publisher chronological output
- Visit Tri-Cities Algolia-backed adapter
- Richland Library LibCal-backed adapter
- Mid-Columbia Libraries saved-HTML adapter
- Tri-City Vibe WordPress-rendered saved-HTML adapter
- Recurrence classification and publisher safety split
- Legacy CSV importer for old `unified_events.csv`
- Unified pipeline spine accepting multiple normalized source batches
- Generic N-source pipeline runner
- Adapter registry for supported source metadata
- Shared adapter contract in `adapters/contract.py`
- Conservative exact-key deduplication with source attribution preservation
- Regression suite
- Pipeline status command

## Status Command

Run:

```powershell
python -m tools.status
```

Expected adapter set after Attempt_21:

```text
Adapters
--------
LegacyUnifiedCSV       MIGRATION_BRIDGE
MidColumbiaLibraries   ACTIVE
RichlandLibrary        ACTIVE
TriCityVibe            ACTIVE
VisitTriCities         ACTIVE
```

Fixture counts depend on whether the local Tri-City Vibe fixture is still representative or has been replaced by a harvested full-page fixture.

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

Visit Tri-Cities plus legacy unified CSV plus Richland Library with dedupe enabled:

```text
all_events: 123
publisher_ready_events: 114
deduplicated_publisher_ready_events: 113
duplicate_groups: 1
recurrence_review_events: 9
skipped_low_quality_dedupe: 30
```

Mid-Columbia Libraries alone through unified pipeline:

```text
all_events: 6
publisher_ready_events: 6
deduplicated_publisher_ready_events: 6
duplicate_groups: 0
recurrence_review_events: 0
skipped_low_quality_dedupe: 0
```

Tri-City Vibe representative fixture:

```text
raw fixture events: 4
normalized fixture events: 4
past events cutoff: enabled
```

## Regression Tests

Run:

```powershell
python -m pytest
```

or on Windows:

```powershell
.\run_tests.bat
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
- [`docs/Attempt_18_RichlandLibrary_SourceStrategy.md`](docs/Attempt_18_RichlandLibrary_SourceStrategy.md) — Richland Library source strategy
- [`docs/Attempt_20_AdapterFramework.md`](docs/Attempt_20_AdapterFramework.md) — shared adapter framework contract
- [`docs/Attempt_21_TriCityVibe.md`](docs/Attempt_21_TriCityVibe.md) — Tri-City Vibe adapter strategy

## GitHub Roadmap Issues

Current execution chain has moved beyond the original issue numbering. `docs/ROADMAP.md` is the canonical milestone source.

Current local milestone chain:

```text
Attempt_14_Registry_Optimizer
  ↓
Attempt_15_Visit_Tri-Cities
  ↓
Attempt_16_Unified_Pipeline
  ↓
Attempt_17_Multi-Source_Deduplication
  ↓
Attempt_18_Richland_Library
  ↓
Attempt_19_Mid-Columbia_Libraries
  ↓
Attempt_20_AdapterFramework
  ↓
Attempt_21_TriCityVibe
  ↓
Attempt_22_Notion_Export
  ↓
Attempt_23_Regression_Test_Suite
  ↓
Attempt_24_Production_Release
```

## Development Rule

Every milestone uses this naming format:

```text
Attempt_##_<Description>
```

The event schema should remain backwards compatible whenever possible.

## Next Planned Milestone

```text
Attempt_22_Notion_Export
```

Before starting broad source expansion, keep the unified pipeline source-agnostic and preserve review queues separately from deduplicated publisher-ready output.
