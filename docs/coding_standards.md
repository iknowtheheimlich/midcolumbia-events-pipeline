# Coding Standards

These are lightweight standards for Cargo Harvester. The goal is maintainability, not ceremonial enterprise cosplay.

## Principles

- Keep source adapters isolated.
- Keep outputs source-agnostic.
- Prefer explicit fields over clever inference.
- Preserve raw/debug data when parsing rendered websites.
- Mark uncertain records for review instead of dropping them.
- Do not wire a source directly to Reddit or Notion.

## Code style

- Python 3.13 target for now.
- Type hints where they clarify intent.
- Small modules with clear boundaries.
- No hidden global state for user settings.
- Avoid hardcoded secrets.

## Error handling

Source adapters should tolerate partial failures.

Good:

- Return fewer records but log which date/source failed.
- Mark missing fields in `review_notes`.
- Preserve debug card data.

Bad:

- Crash the whole weekly run because one source page failed.
- Drop records silently.
- Guess critical data without marking review.

## Review notes

Use short, predictable phrases because downstream logic may depend on them.

Current phrases:

- Missing event name
- Missing date
- Missing source URL
- Missing image URL
- Missing start time
- Missing venue

Fatal markers are defined in `models.py`.

## Output modules

Output modules consume `EventRecord` objects only.

They should not:

- Open websites.
- Parse HTML.
- Know source-specific DOM structure.

## Source modules

Source modules may:

- Use Playwright.
- Parse HTML/JSON/API responses.
- Emit debug metadata.
- Produce `EventRecord` instances.

They should not:

- Generate Reddit posts.
- Push to Notion.
- Make final include/exclude decisions except fatal parse failures.

## Tests

Planned test categories:

- Parser tests from saved card text.
- Dedupe tests.
- Reddit formatting tests.
- EventRecord finalize/review tests.

The parser is where the gremlins live. Test there first.
