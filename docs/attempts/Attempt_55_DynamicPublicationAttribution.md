# Attempt_55_DynamicPublicationAttribution

## Objective

Remove the recurring manual edit required to keep Reddit publication footnotes aligned with the sources used by the production run.

## Decision

Publication attribution is derived from the selected source adapters. The source registry owns two optional presentation fields:

- `attribution_label`: public-facing source name or domain
- `include_in_attribution`: whether the source belongs in publication attribution

Registry priority provides deterministic ordering. No separate attribution-order configuration is maintained.

## Behavior

- Full production runs cite all enabled public sources.
- `--source` limited runs cite only the selected public sources.
- Migration bridges and internal inputs may opt out.
- Duplicate public labels are collapsed without changing order.
- The renderer retains its existing static default for backwards-compatible direct callers.
- Main and Community artifacts receive the same dynamically generated footnote.

## Maintenance boundary

Adding a public source requires setting its attribution metadata in `config/source_registry.json`. No publisher code change is required.

## Validation

Coverage includes:

- one source
- two-source grammar
- three-or-more-source grammar
- migration bridge exclusion
- duplicate label collapse
- empty public source set
- full enabled registry order
