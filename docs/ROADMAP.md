# Mid-Columbia Events Pipeline Roadmap

Canonical project history and forward roadmap for the Mid-Columbia Events Pipeline.

Milestone names use the required format:

```text
Attempt_##_<Description>
```

The event schema should remain backwards compatible whenever possible. Existing fields should not change meaning, type, or required behavior without an explicit migration note.

## Completed Milestones

- [x] Attempt_01_Foundation
- [x] Attempt_02_Saved_HTML
- [x] Attempt_03_URL_Parser
- [x] Attempt_04_Locality_Scoring
- [x] Attempt_05_Publisher
- [x] Attempt_06_Validation
- [x] Attempt_07_Output_Contract
- [x] Attempt_08_Venue_Resolver
- [x] Attempt_09_Master_Resolver
- [x] Attempt_10_Indexed_Resolver
- [x] Attempt_11_Unknown_Venue_Queue
- [x] Attempt_12_Venue_Builder
- [x] Attempt_13_Skeptical_Builder
- [x] Attempt_14_Registry_Optimizer
- [x] Attempt_15_Visit_Tri-Cities
- [x] Attempt_16_Unified_Pipeline
- [x] Attempt_17_Multi-Source_Deduplication
- [x] Attempt_18_Richland_Library
- [x] Attempt_19_Mid-Columbia_Libraries
- [x] Attempt_20_AdapterFramework

## Planned Milestones

- [ ] Attempt_21_TriCityVibe
- [ ] Attempt_22_Notion_Export
- [ ] Attempt_23_Regression_Test_Suite
- [ ] Attempt_24_Production_Release

## Current System Status

The current foundation is stable through Attempt_20.

- Cargo Harvester is operational using saved HTML.
- Event schema is considered stable.
- Venue Registry contains approximately 1,056 venues with Google Place IDs.
- Registry Optimizer generates lookup tables from the Venue Registry.
- Reddit Publisher produces chronological output.
- Unknown venues are separated into a dedicated review queue.
- Active source adapters are registered in `adapters/registry.py`.
- Adapter contract is formalized in `adapters/contract.py`.

## Development Phases

### Phase I: Foundation

Attempts 01-07 established the base harvesting, parsing, validation, publishing, and output contract layers.

### Phase II: Venue Intelligence

Attempts 08-14 established the venue resolution system, unknown venue workflow, registry building, skeptical matching, and optimized lookup generation.

### Phase III: Source Expansion

Attempts 15-19 added the first production-style source adapters and unified multi-source handling.

Completed source work includes:

- Visit Tri-Cities
- Richland Library
- Mid-Columbia Libraries
- Legacy unified CSV migration bridge

### Phase IV: Adapter Framework and Additional Sources

Attempt_20 formalized the adapter manifest and registry contract.

Near-term source targets include:

- Tri-City Vibe
- City of Richland
- additional local civic and community event sources as needed

### Phase V: Publishing, Testing, and Release

Attempts 22-24 will formalize export targets, regression testing, and production readiness.

Primary publishing targets:

- Reddit chronological event posts
- Notion export
- Future structured exports as needed

Production readiness requires a regression test suite before release.

## Schema Compatibility Policy

The event schema is treated as a stable internal contract.

Rules:

- Existing fields should not be removed.
- Existing fields should not change type.
- Existing fields should not change meaning.
- New fields should be optional unless a migration is explicitly documented.
- Publishers should consume documented fields only.
- Source adapters should normalize into the shared event schema rather than creating source-specific publisher branches.

## Milestone Completion Criteria

Each Attempt should be considered complete only when the relevant items are satisfied:

- Source changes are committed.
- Validation passes.
- Publisher output remains chronologically correct.
- Unknown venues route to the review queue instead of polluting the main output.
- Documentation is updated when behavior, schema, or workflow changes.
- ROADMAP.md is updated when milestone status changes.

## Near-Term Priority

Build the next source adapter without modifying publisher, resolver, or canonical schema behavior.

Immediate priority:

1. Parse Tri-City Vibe saved HTML fixture.
2. Identify stable event-card selectors or text-token extraction strategy.
3. Normalize Tri-City Vibe events into canonical event dictionaries.
4. Register `TriCityVibe` only after a normalized fixture exists.
5. Add adapter-specific regression coverage.
