# Roadmap

## Phase 1: Stabilize Cargo Harvester core

Goal: Make AllEvents harvesting reliable enough for weekly use.

Tasks:

- Validate date-sweep counts against manual AllEvents browsing.
- Improve time parsing.
- Improve venue extraction.
- Preserve debug card output for troubleshooting.
- Add basic tests for parsing and dedupe.
- Add Notion writer as a safe follow-up module.
- Add Windows GUI wrapper after CLI path is proven.

## Phase 2: Add source adapters

Goal: Reduce dependence on AllEvents.

Recommended order:

1. Visit Tri-Cities
2. Mid-Columbia Libraries
3. Richland Library
4. Tri-City Vibe
5. Manual CSV correction/import

Each source should emit canonical `EventRecord` objects.

## Phase 3: Improve unification

Goal: Turn multiple feeds into one practical event database.

Tasks:

- Cross-source dedupe.
- Venue normalization.
- City normalization.
- Category inference.
- Confidence scores.
- Review dashboard/export.
- Source priority rules.

## Phase 4: Output automation

Goal: Make weekly Reddit and Notion workflows boring.

Outputs:

- Reddit weekly markdown.
- Notion database push.
- Notion page cover from image URL.
- Calendar/ICS export.
- SITREP event section.
- Optional public event index later.

## Phase 5: Mission Control integration

Goal: Treat events as one module inside the broader Mission Control system.

Potential integrations:

- Morning SITREP.
- Notion operations database.
- Local reminder/watchlist.
- Home Assistant notification hooks if useful.

## Guiding principle

Do not overbuild before the weekly event workflow is stable.

The first victory condition is simple:

```text
Run one command -> get a usable weekly Reddit draft.
```

Everything else can wait its turn in the airlock.
