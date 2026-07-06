# Attempt_19_MidColumbiaLibraries_SourceStrategy

## Purpose

Add Mid-Columbia Libraries as a first-class source adapter without changing the canonical event schema.

## Source

Primary source:

```text
https://midcolumbialibraries.org/events
```

The public upcoming-events page exposes the fields needed by the existing pipeline:

- date
- linked title
- time range
- description
- branch/location
- event type
- audience

## Adapter Name

```text
MidColumbiaLibraries
```

The source name is stable and should not be renamed without a migration note.

## Adapter Boundary

The adapter parses source-specific listing HTML and emits canonical event dictionaries.

It must not:

- publish Reddit markdown
- modify the Venue Registry
- hardcode branch street addresses
- create source-specific schema variants
- perform cross-source deduplication

## Venue Strategy

Mid-Columbia Libraries branch names are passed as raw venue strings for downstream resolver handling.

Examples:

```text
Pasco -> Mid-Columbia Library (Pasco)
West Pasco -> Mid-Columbia Library (West Pasco)
Kennewick -> Mid-Columbia Library (Kennewick)
```

Special non-branch locations are preserved as source venue values:

```text
Online
Offsite
Multiple Branches
Rural Services
```

No street addresses are hardcoded in the adapter.

## Time Strategy

The listing uses mixed human time formats such as:

```text
1:00 - 3:00pm
10:30 - 11:30am
10:00am
```

The parser normalizes these into the existing internal `HH:MM` fixture convention.

## Categories and Audience

The adapter preserves source event type as `category` and preserves audience as `source_audience`.

Publisher classification remains downstream-owned.

## Fixture Strategy

The active normalized fixture is:

```text
fixtures/mid_columbia_libraries/normalized_events.json
```

The fixture includes:

- adult program
- storytime
- elementary program
- teen program
- special event
- branch closure
- missing end-time handling
- multiple branch/city mappings

## Completion Criteria

Attempt_19 is complete when:

- `MidColumbiaLibraries` is registered in `adapters/registry.py`
- normalized fixture loads successfully
- parser tests cover listing token parsing, time parsing, metadata parsing, and fixture shape
- the source runs through `src.pipeline.run_pipeline` without recurrence or dedupe regressions
- `python -m tools.status` includes the source automatically
