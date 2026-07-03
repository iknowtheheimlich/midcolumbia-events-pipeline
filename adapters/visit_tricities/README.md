# Visit Tri-Cities Adapter

Milestone:

```text
Attempt_15_Visit_Tri-Cities
```

## Purpose

This adapter converts Visit Tri-Cities event listing data into the canonical event schema.

## Contract

The adapter must follow:

- `docs/EventSchema.md`
- `docs/SourceAdapters.md`
- `docs/VenueRegistry.md`
- `docs/ResolverPipeline.md`

## Fixture First

Development begins with the fixture pair:

```text
fixtures/visit_tricities/saved_page.html
fixtures/visit_tricities/expected_events.json
```

The adapter is not complete until saved fixture input produces expected canonical event output.

## Source Name

Use stable source identifier:

```text
VisitTriCities
```

## Boundaries

The adapter should:

- Parse Visit Tri-Cities event content.
- Normalize parsed events into the canonical schema.
- Preserve the original source URL.
- Preserve the original venue string.
- Pass raw venue values to the resolver.

The adapter should not:

- Resolve venues directly.
- Modify the Venue Registry.
- Format Reddit Markdown.
- Add publisher-specific logic.
- Perform cross-source deduplication.

## Initial Implementation Target

1. Replace fixture placeholder HTML with a real saved Visit Tri-Cities event listing page.
2. Populate `expected_events.json` with canonical normalized events.
3. Implement parser until fixture output matches expected JSON.
4. Run output through existing resolver and publisher pipeline.
