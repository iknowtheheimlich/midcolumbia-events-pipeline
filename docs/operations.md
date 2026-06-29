# Operations

This document describes the intended weekly operating flow.

## Current weekly flow

Run Windows setup once:

```cmd
setup_windows.bat
```

This installs dependencies, installs the local package in editable mode, and installs Playwright Chromium.

Harvest a date range:

```cmd
run_harvester.bat 2026-07-01 2026-07-07
```

Review outputs:

```text
output\unified_events.csv
output\reddit_weekly_draft.md
output\debug\allevents_cards.json
```

## If counts look too low

AllEvents may not have loaded the full day feed.

Try:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visible --debug
```

Visible mode lets you watch what the browser sees. Debug mode writes the raw card data the parser saw.

## Visit Tri-Cities validation

Run:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visit-tricities --visible --debug
```

Then inspect:

```text
output\debug\visit_tricities_cards.json
output\unified_events.csv
```

If fields are poor, the next move is finding the backend listing endpoint from browser dev tools.

## Review policy

Rows may be marked `Needs Review = Yes` and still be usable.

Fatal:

- Missing event name
- Missing date
- Missing source URL

Nonfatal:

- Missing start time
- Missing venue
- Missing image URL

For Reddit, a missing time becomes `Time TBA`.

## Wi-Fi hiccups

If the connection drops or AllEvents partially loads, rerun the same date range. The output file is regenerated each run.

Future work should add durable cache/resume behavior, but the first stable version can simply rerun.

## Python recommendation

Prefer Python 3.13 for now.

Python 3.14 may work for runtime, but packaging/build tooling is still catching up. Use 3.13 when possible for fewer dependency tantrums.

## Common commands

Install dependencies and package:

```cmd
python -m pip install -r requirements.txt
python -m pip install -e .
python -m playwright install chromium
```

Run CLI directly:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output
```

Run installed command:

```cmd
cargo-harvester --city kennewick --start 2026-07-01 --end 2026-07-07 --output output
```

Run with browser visible and debug output:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visible --debug
```

## Troubleshooting smell test

If `pip install ...` fails, use:

```cmd
python -m pip install ...
```

Bare `pip` can point to a deleted Python install on Windows. It has done this before. It will do it again because Windows enjoys folklore.
