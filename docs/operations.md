# Operations

This document describes the intended weekly operating flow.

## Current weekly flow

Run Windows setup once:

```cmd
setup_windows.bat
```

Harvest a date range:

```cmd
run_harvester.bat 2026-07-01 2026-07-07
```

Review outputs:

```text
output\unified_events.csv
output\reddit_weekly_draft.md
```

## If counts look too low

AllEvents may not have loaded the full day feed.

Try:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visible
```

Visible mode lets you watch what the browser sees.

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

Install dependencies:

```cmd
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Run CLI directly:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output
```

Run with browser visible:

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visible
```

## Troubleshooting smell test

If `pip install ...` fails, use:

```cmd
python -m pip install ...
```

Bare `pip` can point to a deleted Python install on Windows. It has done this before. It will do it again because Windows enjoys folklore.
