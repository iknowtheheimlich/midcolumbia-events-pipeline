# Mid-Columbia Events Pipeline

A local event harvesting, normalization, venue-resolution, and publishing pipeline for Mid-Columbia community event posts.

## Current Status

The current foundation is stable through:

```text
Attempt_14_Registry_Optimizer
```

Core capabilities documented so far:

- Cargo Harvester using saved HTML
- Stable canonical event schema
- Venue Registry with approximately 1,056 venues and Google Place IDs
- Registry Optimizer lookup generation
- Resolver Pipeline with Unknown Venue Queue routing
- Reddit Publisher chronological output

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

## Development Rule

Every milestone uses this naming format:

```text
Attempt_##_<Description>
```

The event schema should remain backwards compatible whenever possible.

## Next Planned Milestone

```text
Attempt_15_Visit_Tri-Cities
```

Before beginning Attempt_15, complete the Attempt_14 Registry Optimizer verification checklist.