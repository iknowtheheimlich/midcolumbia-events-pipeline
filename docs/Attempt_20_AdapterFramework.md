# Attempt_20_AdapterFramework

## Objective

Formalize the source adapter framework so additional event sources can be added without changing the canonical event schema, Reddit publisher, venue resolver, or unified pipeline spine.

## Why This Exists

The project has moved past one-off source parsing. Visit Tri-Cities, Richland Library, Mid-Columbia Libraries, and the legacy CSV bridge now need a shared source boundary so new adapters do not leak source-specific behavior into downstream systems.

The adapter framework keeps the rest of the project boring. Boring is load-bearing.

## Contract

Every source adapter is responsible for converting raw source content into canonical event dictionaries compatible with `docs/EventSchema.md`.

The shared protocol is defined in:

```text
adapters/contract.py
```

Core interface:

```python
parse(content: str) -> list[dict]
```

Adapter output must remain compatible with the existing canonical event schema.

## Registry

Supported adapters are declared in:

```text
adapters/registry.py
```

The registry tracks only source metadata:

- `source_name`
- `adapter_package`
- `status`
- `fixture_path`
- `raw_fixture_path`
- `notes`

Parsing and normalization stay inside the adapter package itself.

## Current Registered Sources

- `VisitTriCities` — active Algolia-backed adapter
- `RichlandLibrary` — active LibCal/Springshare adapter
- `MidColumbiaLibraries` — active saved-HTML listing adapter
- `LegacyUnifiedCSV` — migration bridge for historic unified CSV output

## Non-Goals

Attempt_20 does not:

- change the canonical event schema
- change publisher formatting
- change venue resolver behavior
- add source-specific publisher branches
- merge unknown venue review queues into publisher output
- replace existing adapters that already work

## Tri-City Vibe Implication

Tri-City Vibe appears to be classic WordPress-rendered HTML rather than JSON-backed event data. The saved fixture inspection found WordPress event/listing markup but no obvious `application/ld+json`, `__NEXT_DATA__`, or `startDate` data block.

That means Tri-City Vibe should be added as a DOM/text parser adapter, similar in spirit to the Mid-Columbia Libraries saved-HTML parser, not as a JSON extractor.

## Completion Criteria

Attempt_20 is complete when:

- adapter contract exists
- registry uses the shared manifest structure
- existing registry consumers remain backward-compatible
- documentation reflects the current adapter framework
- roadmap/changelog status reflects completed source milestones accurately
- next source work can begin without touching publisher or resolver code
