# Event Schema

This document defines the canonical event object used throughout the Mid-Columbia Events Pipeline.

## Purpose

Every source adapter normalizes into this schema.

Every downstream component consumes this schema.

The schema is the project's internal API.

## Compatibility Policy

Version: 1.x

Rules:

- Existing fields SHALL NOT be removed.
- Existing fields SHALL NOT change meaning.
- Existing fields SHALL NOT change type.
- New fields SHOULD be optional.
- Breaking changes require a documented schema version increment.

## Canonical Fields

| Field | Type | Required | Description |
|------|------|:--------:|-------------|
| title | string | Yes | Event title |
| venue | string | Yes | Original venue name |
| venue_id | string/null | No | Canonical Venue Registry identifier |
| address | string/null | No | Street address |
| city | string | Yes | Normalized city |
| start_date | date | Yes | Event start date |
| end_date | date/null | No | Event end date |
| start_time | time/null | No | Event start time |
| end_time | time/null | No | Event end time |
| url | string | Yes | Source URL |
| source | string | Yes | Source adapter name |
| category | string/null | No | Optional category |
| description | string/null | No | Optional description |

## Optional Enrichment Fields

These fields may be provided by source adapters when available. Downstream consumers must treat them as optional.

| Field | Type | Description |
|------|------|-------------|
| external_url | string/null | External event or registration URL distinct from the source listing URL |
| is_series | boolean/null | True when the source event appears to represent a recurring series or multi-date container |
| recurrence_note | string/null | Human-readable recurrence or repeat note from source |
| source_event_id | string/null | Source-specific event identifier |
| source_start_timestamp | integer/null | Source-provided raw start timestamp |
| source_end_timestamp | integer/null | Source-provided raw end timestamp |

## Processing Contract

Harvesters -> Parsers -> Canonical Event Schema -> Venue Resolver -> Validation -> Publisher

Components may enrich events but should not reinterpret existing fields.

## Validation

Validation should verify:

- Required fields present.
- Valid dates.
- Valid times.
- Non-empty title.
- Source identified.
- URL present.

Validation failures should stop publication rather than silently producing malformed output.

## Future Expansion

Future fields may include:

- recurrence
- organizer
- tags
- cost
- age_restrictions
- coordinates

These additions should remain backward compatible.
