# Architecture

Cargo Harvester is a source-to-output event pipeline for Mid-Columbia/Tri-Cities event listings.

The central rule is simple:

```text
Sources -> Canonical EventRecord -> Outputs
```

No output should depend directly on a source website. All sources must emit the same canonical `EventRecord` shape before the data reaches Reddit, Notion, calendar exports, SITREP, or any future target.

## Current flow

```text
AllEvents date sweep
      |
      v
Listing URL discovery
      |
      v
Event detail page scrape
      |
      v
EventRecord list
      |
      +--> unified_events.csv
      +--> reddit_weekly_draft.md
```

## Why date sweep exists

The AllEvents city/all page does not reliably load a comprehensive list. It often returns a partial feed unless a date is supplied. The adapter therefore scans one date at a time and tries several likely date-filter URL patterns.

However, the listing page is not treated as the source of truth. It may display events outside the requested date. Listing pages are now used for discovery only: collect candidate event URLs, then open each detail page and extract the real title/date/time/venue from the event page itself.

## Module boundaries

```text
src/cargo_harvester/models.py
```
Defines the canonical event shape and review/fatal logic.

```text
src/cargo_harvester/sources/
```
Source adapters. Each adapter should convert raw site data into `EventRecord` objects.

```text
src/cargo_harvester/core.py
```
Shared pipeline operations: dedupe and CSV output.

```text
src/cargo_harvester/reddit.py
```
Reddit markdown output. It consumes `EventRecord`; it should not know how any source works.

```text
src/cargo_harvester/cli.py
```
Command-line runner for local testing and weekly use.

## Planned outputs

- Notion database writer
- Windows GUI wrapper
- Calendar/ICS export
- SITREP integration
- Source confidence report

## Design notes

Keep the pipeline boring. Boring systems survive Tuesdays.

When in doubt, add a source adapter or output adapter. Do not mix source-specific parsing into downstream output logic.
