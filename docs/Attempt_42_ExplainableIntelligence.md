# Attempt_42_ExplainableIntelligence

## Objective

Standardize provenance for inferred event fields without changing existing values or
forcing downstream consumers to migrate immediately.

## Contract

Each explainable field may be represented additively as:

```json
{
  "intelligence": {
    "category": {
      "value": "Music/Comedy",
      "confidence": 0.92,
      "reason": "keyword=live music"
    }
  }
}
```

Existing flat fields remain authoritative for backwards compatibility.

## Initial coverage

- venue registry resolution
- geographic scope
- semantic category
- editorial display style
- program grouping

## Audit

The publisher audit summarizes intelligence decisions by field and reason. It does not
reimplement subsystem-specific reasoning.

## Non-goals

- changing classification algorithms
- changing deduplication behavior
- replacing flat fields
- inventing confidence where no inference occurred
