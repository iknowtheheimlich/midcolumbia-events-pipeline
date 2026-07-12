# Attempt_36_SourceRegistry

## Objective

Centralize source enablement and operating metadata, preserve legacy adapter APIs, and emit per-source production telemetry.

## Registry

`config/source_registry.json` owns:

- source identity
- enabled state
- priority
- implementation status
- adapter package
- fixture paths
- operational notes

`SOURCE_REGISTRY` exposes all configured sources. `AVAILABLE_ADAPTERS` remains a backwards-compatible manifest of implemented adapters only.

Planned sources may be configured before implementation, but remain disabled and excluded from `AVAILABLE_ADAPTERS`.

## Production metrics

Each live run writes `artifacts/reddit/Source_Metrics.txt` with:

- harvested count
- content rejection count
- duplicate events removed
- main-post contribution count
- community-post contribution count
- review count
- rejected count
- harvest warnings

Deduplicated events credit every contributing source for coverage. Duplicate removal is charged only to non-primary source members in each duplicate group.

## Compatibility

- `AVAILABLE_ADAPTERS` remains available.
- `get_adapter()` remains available.
- `list_source_names()` retains alphabetical ordering.
- Existing output arguments remain unchanged.
