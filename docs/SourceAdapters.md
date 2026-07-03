# Source Adapters

This document defines the contract for adding event sources to the Mid-Columbia Events Pipeline.

## Purpose

A source adapter is responsible for converting one external source into the canonical event schema.

Adapters should isolate source-specific weirdness so the rest of the pipeline stays boring. Boring is good. Boring ships.

## Adapter Lifecycle

```text
Fetch
  ↓
Parse
  ↓
Normalize
  ↓
Venue Resolution
  ↓
Validation
  ↓
Publish
```

## Adapter Responsibilities

Each adapter must:

- Identify its source name.
- Acquire source content or accept saved source content.
- Parse raw event data.
- Normalize parsed data into the canonical event schema.
- Preserve the source URL.
- Preserve the original venue string.
- Avoid guessing unresolved venues.
- Route unknown venues through the shared Unknown Venue Queue.
- Produce events that pass validation before publishing.

## Adapter Non-Responsibilities

Adapters must not:

- Publish Reddit output directly.
- Format Markdown output.
- Modify the Venue Registry directly during normal parsing.
- Create source-specific event schema variants.
- Add publisher exceptions for source-specific fields.
- Silently drop malformed events without logging or review output.

## Required Output

Every adapter must emit canonical event objects compatible with `docs/EventSchema.md`.

Required minimum fields:

- `title`
- `venue`
- `city`
- `start_date`
- `url`
- `source`

Optional fields should be populated when available, but missing optional data should not block publication unless required by a downstream rule.

## Source Names

Use stable source identifiers.

Examples:

- `AllEvents`
- `VisitTriCities`
- `TriCityVibe`
- `RichlandLibrary`
- `MidColumbiaLibraries`

Source names should not change once events are being emitted unless a migration note is added.

## Normalization Rules

Adapters should normalize:

- Whitespace
- Date formats
- Time formats
- City names
- URLs
- Empty strings to null where appropriate

Adapters should preserve:

- Original event title text as much as possible
- Original venue string before resolver enrichment
- Source URL

## Venue Handling

Venue handling belongs to the resolver pipeline, not individual adapters.

Adapters pass the best available raw venue value to the canonical event schema.

The resolver then determines:

- Canonical venue match
- Venue Registry ID
- Google Place ID linkage
- Unknown venue queue routing

Unknown venues must not be guessed into existence by a source adapter.

## Deduplication

Adapters do not perform cross-source deduplication.

Cross-source deduplication belongs to a shared deduplication stage planned for:

```text
Attempt_16_Multi-Source_Deduplication
```

Adapters may remove exact duplicates within a single source response when the duplicate is clearly caused by source markup repetition.

## Error Handling

Adapters should report:

- Missing title
- Missing date
- Missing venue
- Missing URL
- Invalid date parsing
- Invalid time parsing
- Empty event groups
- Unexpected source layout changes

Errors should produce reviewable logs or queues rather than quiet failures.

## Test Expectations

Each adapter should include test fixtures where practical:

- Saved HTML or source sample
- Parsed intermediate output
- Final normalized event objects
- Validation pass/fail expectations

Tests should confirm:

- Required fields are populated
- Dates parse correctly
- Times parse correctly
- Source name is stable
- Unknown venues are routed correctly
- Publisher output remains chronological after adapter integration

## Attempt_15 Adapter Target

The next planned adapter is:

```text
Attempt_15_Visit_Tri-Cities
```

Attempt_15 should add Visit Tri-Cities as a source adapter without changing the canonical event schema unless a backwards-compatible optional field is required.