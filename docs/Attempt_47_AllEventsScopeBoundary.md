# Attempt_47_AllEventsScopeBoundary

## Objective

Prevent AllEvents global recommendation cards from entering the local event model.

AllEvents city pages place a visible divider after the final applicable local result:

```text
Results for selected filters around the globe
```

The JSON-LD remains the source of event detail. The visible card section now determines eligibility when that divider is present.

## Contract

For a bounded city page:

```text
local card event IDs before divider
INTERSECT
JSON-LD event IDs
=
eligible events
```

Cards and JSON-LD records after the divider are excluded.

If the divider is absent, existing JSON-LD behavior is preserved for backwards compatibility.

## Production observation

The captured 2026-07-12 Kennewick page contained 64 unique JSON-LD event IDs, and all 64 appeared before the global-results divider. Therefore this milestone is a guardrail rather than a production-count correction for that snapshot.

## Regression coverage

- JSON-LD event before the divider is retained.
- JSON-LD event represented only after the divider is rejected.
- Pages without the divider continue to trust JSON-LD.
- Cross-city deduplication remains unchanged.

Generated artifacts remain outside fixture directories.
