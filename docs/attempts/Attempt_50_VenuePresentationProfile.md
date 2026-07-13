# Attempt_50_VenuePresentationProfile

## Objective

Make venue presentation an explicit upstream contract rather than a collection of
renderer and editorial guesses.

## Contract

Canonical identity remains unchanged. Publisher projection now carries:

- `display_venue`
- `display_city`
- `display_url`
- `venue_presentation_reason`
- `suppress_display_city`

The presentation profile consumes registry-enriched canonical fields and emits the
single human-facing representation used by every downstream presentation client.

## Initial curated profiles

- The Emerald of Siam
- Solar Spirits
- Goose Ridge Winery

Unknown venues retain deterministic registry/source fallback behavior. Notion-authored
`venue_reddit_combo` fragments remain opaque and authoritative.

## Boundaries

- Occurrence resolution continues to use canonical identity.
- Editorial style may clean titles but does not choose venue names or URLs.
- The renderer consumes the final editorial presentation without venue-specific rules.

## Regression safety

Existing `PublisherEvent` construction remains compatible because presentation fields
are additive and optional. Canonical venue and source fields are preserved for audit,
identity, and provenance.
