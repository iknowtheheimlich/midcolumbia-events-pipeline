# Attempt_38_CategoryIntelligence

## Objective

Enrich canonical events with the project's semantic category vocabulary before publication.

## Contract

The layer emits:

- `category`
- `category_confidence`
- `category_reason`

Existing valid semantic categories are preserved with confidence `1.0`.
Deterministic source-category and keyword rules classify known patterns.
Unmatched events remain unclassified and therefore stay in the editorial review queue.

## Boundaries

- Collectors preserve source vocabulary as `source_category`.
- Category intelligence maps event meaning into the shared semantic vocabulary.
- The publishing contract maps semantic categories to `MAIN` or `COMMUNITY`.
- Renderers do not classify.

## Backwards compatibility

`run_pipeline(..., enrich_categories=False)` remains the default. The live production publisher explicitly enables category enrichment.

## Operational behavior

`Publisher_Audit.txt` reports category counts and classification reasons. Low-confidence or unmatched events remain visible in review rather than being silently guessed.
