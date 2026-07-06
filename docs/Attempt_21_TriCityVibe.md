# Attempt_21_TriCityVibe

## Objective

Add Tri-City Vibe as a source adapter without changing the canonical event schema, Reddit publisher, venue resolver, or unified pipeline spine.

## Source Behavior

Tri-City Vibe renders events as classic WordPress HTML. The events listing exposes repeated entries with this visible sequence:

```text
MM/DD/YYYY Weekday Time
Event title link
Venue
City, ST
```

The page also contains a `Past Events` section, which must be treated as a hard cutoff for publisher-ready harvesting.

## Adapter Package

```text
adapters/tricity_vibe/
    __init__.py
    config.py
    parser.py
```

## Parser Strategy

The parser uses ordered visible text/link token extraction rather than relying on brittle CSS selectors.

This is deliberate. The source is WordPress-rendered and may shift classes/theme markup while preserving the visible event structure.

Parsed fields:

- `title`
- `venue`
- `city`
- `start_date`
- `start_time`
- `end_time`
- `url`
- `source`
- `category`
- `source_event_id`
- `source_location`

## Known Source Defects

The live source contains occasional typos in listing text. Attempt_21 includes conservative tolerance for known defects:

- `Thursady` is tolerated as a weekday typo.
- `6pjm` is normalized to `6pm`.

Weekday text is non-authoritative. The calendar date is the canonical date value.

## Fixture Scope

Initial fixture coverage is representative rather than full-page:

```text
fixtures/tricity_vibe/raw_events.html
fixtures/tricity_vibe/normalized_events.json
```

The fixture intentionally includes:

- normal time range
- single start time
- weekday typo
- time typo
- out-of-state city parsing
- `Past Events` cutoff

## Registry

The adapter is registered as active in:

```text
adapters/registry.py
```

Source identifier:

```text
TriCityVibe
```

## Tests

Regression coverage lives in:

```text
tests/test_tricity_vibe_adapter.py
```

The tests verify:

- registry wiring
- fixture parsing
- `Past Events` cutoff
- range and typo time parsing
- city parsing
- normalized fixture shape

## Completion Criteria

Attempt_21 is complete when:

- Tri-City Vibe adapter package exists
- parser extracts representative saved-HTML events
- normalized fixture exists
- adapter is registered
- regression tests pass locally
- `tools.status` reports `TriCityVibe` as active

## Follow-Up

Replace the representative fixture with a full harvested page fixture once local harvesting is stable for this source.
