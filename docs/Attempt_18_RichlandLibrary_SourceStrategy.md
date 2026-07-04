# Attempt_18_Richland_Library Source Strategy

## Objective

Add Richland Library events as a normalized source in the unified Mid-Columbia Events Pipeline.

## Adapter Rule

Richland Library must normalize into the canonical event schema and then enter the shared pipeline:

```text
Richland Library source
  ↓
canonical normalized events
  ↓
recurrence classification
  ↓
publisher safety split
  ↓
deduplication
  ↓
deduplicated publisher-ready output
```

The adapter must not contain publisher formatting, cross-source deduplication, or venue registry mutation logic.

## Source Discovery Plan

Before parser implementation, identify the actual event backend used by the Richland Library calendar.

Preferred source order:

1. Official JSON/API/calendar endpoint.
2. Official ICS feed.
3. Structured data embedded in the page.
4. Saved HTML only if no structured source exists.

## Expected Fields

Map source data into:

| Canonical Field | Richland Library Source |
|---|---|
| title | Event title |
| venue | `Richland Library` unless source provides a more specific room/location |
| venue_id | nullable until registry resolution |
| address | Richland Library address when available |
| city | Richland |
| start_date | Event start date |
| end_date | Event end date or start date |
| start_time | Event start time, nullable for all-day events |
| end_time | Event end time, nullable |
| url | Event detail URL |
| source | `RichlandLibrary` |
| category | Program/category/audience when available |
| description | Description/summary when available |

## Optional Metadata

Adapters may preserve:

- `source_event_id`
- `source_calendar_id`
- `source_location`
- `source_room`
- `age_audience`
- `registration_required`
- `source_raw_start`
- `source_raw_end`

All optional fields must remain optional for downstream consumers.

## Fixture Workflow

Use saved fixtures first.

Target files:

```text
fixtures/richland_library/raw_events.json
fixtures/richland_library/normalized_events.json
```

If the backend is ICS instead of JSON:

```text
fixtures/richland_library/raw_events.ics
fixtures/richland_library/normalized_events.json
```

## Acceptance Criteria

- Source backend identified.
- Fixture capture workflow added.
- Adapter normalizes fixtures into canonical events.
- Normalized events run through `run_pipeline` as a `SourceBatch`.
- Combined run with VTC + legacy + Richland Library produces deduplicated publisher-ready output.
- Recurring/library series events route to recurrence review if unsafe to publish directly.
