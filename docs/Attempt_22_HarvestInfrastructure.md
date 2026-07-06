# Attempt_22_Harvest_Infrastructure

## Objective

Build a reproducible harvest layer that can refresh raw fixtures, regenerate normalized fixtures, and smoke-test the existing pipeline with one command.

## Primary command

```powershell
python -m tools.harvest_all
```

## Offline regeneration

Use saved raw fixtures only:

```powershell
python -m tools.harvest_all --skip-fetch
```

## Single-source regeneration

```powershell
python -m tools.harvest_all --source VisitTriCities
python -m tools.harvest_all --source TriCityVibe --skip-fetch
```

## Legacy bridge regeneration

The legacy bridge does not have a raw fixture path. It reuses the existing normalized fixture unless a CSV is supplied:

```powershell
python -m tools.harvest_all --source LegacyUnifiedCSV --legacy-input path\to\unified_events.csv
```

## Fixture layers

Each active source now follows the same two-layer fixture pattern:

1. `raw_fixture_path` from `adapters.registry`
2. `fixture_path` normalized canonical events from `adapters.registry`

The harvest layer reads source metadata from the registry. It does not maintain duplicate fixture path maps.

## Adapter coverage

Current harvesters:

- `VisitTriCities` — fetches Algolia JSON payload and normalizes through the existing VisitTriCities adapter.
- `RichlandLibrary` — fetches LibCal monthly HTML fragments and normalizes through the existing parser.
- `MidColumbiaLibraries` — fetches public event listing HTML and normalizes through the existing parser.
- `TriCityVibe` — fetches WordPress-rendered event listing HTML and normalizes through the existing parser.
- `LegacyUnifiedCSV` — preserves the migration bridge and only regenerates from CSV when `--legacy-input` is supplied.

## Pipeline smoke

Unless `--skip-pipeline-smoke` is supplied, `tools.harvest_all` runs the existing source-agnostic pipeline after fixture regeneration and prints:

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
