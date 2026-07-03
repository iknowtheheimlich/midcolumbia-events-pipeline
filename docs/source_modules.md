# Source Modules

Source adapters live in:

```text
src/cargo_harvester/sources/
```

Each source module is responsible for one external event source and must return canonical `EventRecord` objects.

## Source adapter contract

A source adapter should:

1. Fetch or render source data.
2. Extract raw event records.
3. Convert records into `EventRecord`.
4. Call `.finalize()` before returning.
5. Leave downstream formatting to output modules.

It should not:

- Generate Reddit markdown.
- Push to Notion.
- Write directly to the final database unless explicitly designed as an output module.
- Hide errors silently when a useful review note would help.

## Current adapter

```text
sources/allevents.py
```

Uses Playwright to open AllEvents with date-filtered URLs. This exists because the city/all page is incomplete without date constraints.

## Planned adapters

Recommended order:

1. `visit_tricities.py`
2. `mcl.py`
3. `richland_library.py`
4. `tricityvibe.py`
5. `manual_csv.py`

## Normalization rules

Source adapters may normalize obvious fields but should avoid overcorrecting.

Good:

- Trim whitespace.
- Extract URL/image URL.
- Use fallback city when the source page is city-specific.
- Flag missing time as review, not fatal.

Bad:

- Guess a specific time from vague text.
- Drop records because the venue is missing.
- Merge duplicates across sources without a confidence check.

## Debug outputs

Adapters that use rendered pages should be able to preserve raw card/debug data. This is useful when a site changes layout and the parser starts acting possessed.

## Naming convention

Use lowercase snake_case module names:

```text
visit_tricities.py
richland_library.py
manual_csv.py
```

Keep one source per file unless two sources share the exact same platform/API.
