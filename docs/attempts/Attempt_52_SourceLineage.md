# Attempt_52_SourceLineage

## Objective

Separate event authorship from event discovery so syndicated aggregator copies do not
count as independent authority.

## Contract

The compatibility `source` field remains unchanged. Occurrence resolution now enriches
records with:

- `origin_source`
- `discovery_source`
- `is_syndicated`
- `intelligence.source_lineage`

Resolved occurrences additionally expose:

- `origin_sources`
- `discovery_sources`
- `corroborating_sources`
- `independent_source_count`

## Initial lineage rule

AllEvents records associated with Richland Public Library are treated as syndicated
copies of `RichlandLibrary` events. AllEvents remains the discovery source and its URL is
preserved in occurrence provenance.

## Authority

Native-origin records outrank syndicated copies during primary-record selection. Source
registry priority and record richness remain secondary tie-breakers.

## Boundaries

This attempt does not change occurrence-match thresholds, categories, venue presentation,
or rendering. New syndication relationships should be added only when the origin can be
determined reliably from event metadata.
