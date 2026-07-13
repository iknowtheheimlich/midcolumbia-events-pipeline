# Attempt_45_AllEventsStructuredExtraction

## Objective

Harden AllEvents saved-city-page extraction against the production JSON-LD shapes observed in the July 13 Kennewick snapshot.

## Finding

The collector already used JSON-LD and already traversed `ItemList -> ListItem -> item -> Event`. Reimplementing that path would add code without capability.

The saved page instead exposed four concrete fidelity gaps:

- date-only values were represented as midnight clock times;
- `organizer` may be a list of organizations;
- titles and descriptions may contain HTML entities;
- the same occurrence may appear in direct Event blocks and ItemLists.

## Changes

- Date-only `startDate` and `endDate` values now emit dates without fabricated times.
- Explicit datetime values continue to emit `HH:MM` times.
- Organizer lists are normalized into a stable comma-separated organization field.
- HTML entities are decoded during scalar text normalization.
- Location arrays use the first structured Place object.
- Duplicate occurrence identity remains URL + date + explicit time.
- Malformed JSON-LD blocks are skipped without aborting the page.
- Added a compact saved-city-page regression fixture modeled on the uploaded Kennewick page.

## Boundaries

No changes were made to live fetching, venue intelligence, category intelligence, occurrence resolution, program grouping, or presentation.
