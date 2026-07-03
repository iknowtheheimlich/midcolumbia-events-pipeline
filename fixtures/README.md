# Fixtures

Fixtures provide stable parser and regression inputs for the Mid-Columbia Events Pipeline.

Each source fixture should include:

```text
saved_page.html
expected_events.json
```

## Purpose

Fixtures make parser behavior repeatable.

They support:

- Source adapter development
- Schema validation
- Venue resolver verification
- Unknown Venue Queue verification
- Publisher regression testing
- Future Notion export testing

## Source Fixture Layout

```text
fixtures/
├── allevents/
│   ├── saved_page.html
│   └── expected_events.json
├── visit_tricities/
│   ├── saved_page.html
│   └── expected_events.json
├── tri_city_vibe/
│   ├── saved_page.html
│   └── expected_events.json
├── richland_library/
│   ├── saved_page.html
│   └── expected_events.json
└── mid_columbia_libraries/
    ├── saved_page.html
    └── expected_events.json
```

## Rules

- Fixture HTML should be saved source content, not live scraped content.
- Expected JSON should use the canonical event schema from `docs/EventSchema.md`.
- Expected JSON should preserve source URL and original venue string.
- Unknown venues should remain unresolved in expected output unless the fixture is explicitly testing a known venue.
- Fixtures should be deterministic and safe to compare in regression tests.

## Attempt_15 Usage

`Attempt_15_Visit_Tri-Cities` should begin with:

```text
fixtures/visit_tricities/saved_page.html
fixtures/visit_tricities/expected_events.json
```

The adapter is complete when it can parse the saved HTML and produce output matching the expected JSON.