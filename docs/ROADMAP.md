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

## Planned Milestones

- [ ] Attempt_15_Visit_Tri-Cities
- [ ] Attempt_16_Multi-Source_Deduplication
- [ ] Attempt_17_Richland_Library
- [ ] Attempt_18_Mid-Columbia_Libraries
- [ ] Attempt_19_Notion_Export
- [ ] Attempt_20_Production_Release

## Current System Status

The current foundation is stable.

- Cargo Harvester is operational using saved HTML.
- Event schema is considered stable.
- Venue Registry contains approximately 1,056 venues with Google Place IDs.
- Registry Optimizer generates lookup tables from the Venue Registry.
- Reddit Publisher produces chronological output.
- Unknown venues are separated into a dedicated review queue.

## Development Phases

### Phase I: Foundation

Attempts 01-07 established the base harvesting, parsing, validation, publishing, and output contract layers.

### Phase II: Venue Intelligence

Attempts 08-14 established the venue resolution system, unknown venue workflow, registry building, skeptical matching, and optimized lookup generation.

### Phase III: Source Expansion

Attempts 15-18 will add additional source adapters and deduplication across event sources.

Target sources include:

- Visit Tri-Cities
- Tri-City Vibe
- Richland Library
- Mid-Columbia Libraries
- Additional local civic and community event sources as needed

### Phase IV: Publishing and Release

Attempts 19-20 will formalize export targets and production readiness.

Primary publishing targets:

- Reddit chronological event posts
- Notion export
- Future structured exports as needed

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

Finish the Venue Registry system before adding more source complexity.

Immediate priority:

1. Verify Registry Optimizer output tables.
2. Confirm resolver uses generated lookup tables correctly.
3. Confirm unknown venue queue remains clean and reviewable.
4. Lock Attempt_14 behavior.
5. Begin Attempt_15_Visit_Tri-Cities.
