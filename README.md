# Mid-Columbia Events Pipeline

A local event-ingestion pipeline for Tri-Cities weekly Reddit posts and the broader Mission Control event database.

Current status: Cargo Harvester core is being formalized from the earlier prototype ZIPs.

## What it does now

- Sweeps AllEvents by date range instead of relying on the incomplete city/all page.
- Uses Playwright/Chromium so the site loads like a real browser.
- Normalizes event records into one canonical schema.
- Deduplicates rows.
- Writes a CSV output.
- Generates a Reddit weekly draft.
- Can merge manual CSV rows into the same unified event feed.
- Can optionally include rendered Visit Tri-Cities event listings.
- Can write source debug JSON for parser diagnosis.

## Windows setup

Run:

```cmd
setup_windows.bat
```

Then harvest a week:

```cmd
run_harvester.bat 2026-07-01 2026-07-07
```

Outputs:

```text
output\unified_events.csv
output\reddit_weekly_draft.md
output\debug\allevents_cards.json
```

## Direct CLI

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output
```

Debug mode:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --debug
```

Visible browser mode:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visible
```

Include Visit Tri-Cities:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visit-tricities --debug
```

Manual CSV merge:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --manual-csv examples\manual_events_template.csv
```

Manual-only run:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --skip-allevents --manual-csv examples\manual_events_template.csv
```

## Project architecture

```text
src/cargo_harvester/
  models.py              Canonical EventRecord model
  core.py                CSV output, debug output, and dedupe helpers
  cli.py                 Command-line runner
  reddit.py              Reddit weekly draft exporter
  sources/
    base.py              Source adapter contract
    allevents.py         AllEvents date-sweep adapter
    manual_csv.py        Manual CSV intake adapter
    visit_tricities.py   Visit Tri-Cities rendered-page adapter
```

Planned modules:

```text
notion.py                Notion database writer
sources/mcl.py
sources/richland_library.py
gui.py                   Windows GUI wrapper
```

## Python version note

Prefer Python 3.13 for now. Python 3.14 is usable for some pieces, but packaging support is still catching up in the ecosystem.

## Design rule

All sources feed a unified event model. Reddit, Notion, calendar, and SITREP outputs consume that unified model. No source should wire directly to the broadcast array.
