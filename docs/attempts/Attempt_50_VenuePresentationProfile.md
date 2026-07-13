# Attempt_50_VenuePresentationProfile

## Objective

Make venue presentation an explicit upstream contract rather than a collection of renderer and editorial guesses.

## Contract

Canonical identity remains unchanged. Registry-enriched events and Publisher Projection now carry:

- `display_venue`
- `display_city`
- `display_url`
- `venue_presentation_reason`
- `suppress_display_city`
- `venue_short_name`
- `parent_display_name`

`VenueRecord` supports optional presentation fields:

- `display_name`
- `display_url`
- `display_city`
- `suppress_display_city`
- `short_name`
- `parent_display_name`

Existing generated registry rows remain valid because all new fields are optional.

## Authority order

1. Presentation fields emitted by a matched Venue Registry record.
2. Curated compatibility rules in `config/venue_presentation.json` for unresolved legacy records.
3. Registry or source fallback.

The projection consumes the resulting presentation model. Editorial style may clean titles, but authoritative venue presentation is preserved.

## Initial curated compatibility profiles

- The Emerald of Siam
- Solar Spirits
- Goose Ridge Winery

Unknown venues retain deterministic registry/source fallback behavior. Notion-authored `venue_reddit_combo` fragments remain opaque and authoritative.

## Boundaries

- Occurrence resolution continues to use canonical identity.
- Editorial style owns title cleanup, not venue identity.
- The renderer consumes final display fields without venue-specific rules.
- No logos, colors, or branding metadata are introduced.

## Regression safety

Existing registry JSON and `PublisherEvent` construction remain compatible because presentation fields are additive and optional. Canonical venue and source fields remain available for audit, identity, and provenance.
