# Attempt 73 — Venue Category Intelligence

## Goal

Move stable recurring category knowledge out of expanding title-keyword lists and into venue-level intelligence.

A venue category hint is a prior, not a final decision. Stronger event evidence remains authoritative.

## Classifier precedence

1. Explicit title rules
2. Existing or source category
3. Remaining deterministic title rules
4. Venue category hint
5. Venue-type intelligence
6. Description evidence
7. Review queue

Venue hints never override stronger title or source evidence.

## Initial venue hints

| Venue | Category hint | Confidence | Strength |
|---|---|---:|---|
| Art YOUR Way | Classes/Workshops | 0.96 | strong |
| CBC Planetarium | Lectures/Talks | 0.94 | strong |
| Jokers Comedy Club | Music/Comedy | 0.95 | strong |
| Richland Public Library | Community Programs | 0.63 | soft |
| Mid-Columbia Libraries | Community Programs | 0.61 | soft |

Multipurpose venues such as wineries, breweries, convention centers, parks, and fairgrounds are intentionally excluded.

## Explainability

Venue-derived decisions report:

```text
venue_hint=<canonical venue>;strength=<strong|soft>
```

The category confidence is inherited from the venue hint record.

## Required behavior

- `Fundraiser at Art YOUR Way` → `Fundraisers`
- `Open Mic at a winery` → `Karaoke/Open Mic`
- `Aloha Pineapple` at Art YOUR Way → `Classes/Workshops`
- `Paint Your Pet` at Art YOUR Way → `Classes/Workshops`
- Existing source categories outrank venue hints.
- Unlisted multipurpose venues receive no venue prior.

## Validation

Full regression suite after implementation:

```text
299 passed
```

## Result

Venue category decisions are now encoded once at the venue level, remain subordinate to stronger evidence, and expose an auditable reason instead of requiring additional title-specific keyword rules.
