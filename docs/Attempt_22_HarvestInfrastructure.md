# Attempt_22_Harvest_Infrastructure

## Objective

Build a reproducible harvest layer that can fetch live raw source data, normalize it, and smoke-test the existing pipeline with one command without mutating golden regression fixtures by default.

## Primary command

```powershell
python -m tools.harvest_all
```

Default behavior:

- fetches live raw source data where possible
- caches raw fixtures at each adapter's `raw_fixture_path`
- writes live normalized output under `generated/harvest/<SourceName>/normalized_events.json`
- runs pipeline smoke against the in-memory harvested events
- preserves tracked golden normalized fixtures

## Offline regeneration

Use saved raw fixtures when available and otherwise reuse the existing normalized fixture:

```powershell
python -m tools.harvest_all --skip-fetch
```

## Single-source regeneration

```powershell
python -m tools.harvest_all --source VisitTriCities
python -m tools.harvest_all --source TriCityVibe --skip-fetch
```

## Golden fixture refresh

Tracked normalized fixtures are regression fixtures. They are only rewritten when explicitly requested:

```powershell
python -m tools.harvest_all --write-normalized-fixtures
```

Use this only when intentionally refreshing the test corpus, then immediately run:

```powershell
python -m pytest
```

## Legacy bridge regeneration

The legacy bridge does not have a raw fixture path. It reuses the existing normalized fixture unless a CSV is supplied:

```powershell
python -m tools.harvest_all --source LegacyUnifiedCSV --legacy-input path\to\unified_events.csv
```

## Fixture layers

Each active source has registry-defined paths:

1. `raw_fixture_path` from `adapters.registry`
2. `fixture_path` normalized canonical events from `adapters.registry`

The harvest layer reads source metadata from the registry. It does not maintain duplicate fixture path maps.

## Generated output

Live normalized harvest output is written outside tracked fixture paths:

```text
generated/harvest/<SourceName>/normalized_events.json
```

This lets production harvests and regression tests coexist without corrupting each other. Novel concept. Apparently useful.

## Adapter coverage

Current harvesters:

- `VisitTriCities` — fetches Algolia JSON payload and normalizes through the existing VisitTriCities adapter.
- `RichlandLibrary` — fetches LibCal monthly HTML fragments and normalizes through the existing parser; if live fetch fails and a normalized fixture exists, the harvester preserves that fixture and reports a warning.
- `MidColumbiaLibraries` — fetches public event listing HTML and normalizes through the existing parser.
- `TriCityVibe` — fetches WordPress-rendered event listing HTML and normalizes through the existing parser.
- `LegacyUnifiedCSV` — preserves the migration bridge and only regenerates from CSV when `--legacy-input` is supplied.

## Pipeline smoke

Unless `--skip-pipeline-smoke` is supplied, `tools.harvest_all` runs the existing source-agnostic pipeline against the current harvest results and prints:

- Input
- Publisher
- Deduplicated
- Duplicate Groups
- Series Review
- Low Quality Skips

## Boundaries

Attempt_22 is infrastructure only.

No intentional changes were made to:

- canonical event schema
- publisher
- resolver
- deduplication
- recurrence classifier

## Verification

Run:

```powershell
python -m tools.harvest_all --skip-fetch
python -m pytest
```

The expected regression target entering Attempt_22 is 21 passing tests.
