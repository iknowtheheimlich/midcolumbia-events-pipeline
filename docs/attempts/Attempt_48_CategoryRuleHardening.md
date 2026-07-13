# Attempt_48_CategoryRuleHardening

## Objective

Reduce visible editorial misclassification without widening maintenance-heavy heuristics.

## Changes

- Replaced raw substring matching with ordered compiled phrase and whole-word rules.
- Removed bare `play` and bare `faith` as category triggers.
- Separated title, title-plus-venue context, and description evidence.
- Title evidence now outranks promotional description prose.
- Added first-class `Food & Drink` and `Lectures/Talks` categories.
- Added explicit handling for films, lectures/history talks, sports competitions, food pairings, and performers at hospitality venues.
- Preserved unmatched events in review.
- Preserved opt-in category enrichment and existing semantic category authority.

## Non-goals

- No occurrence-resolution tuning.
- No venue-registry changes.
- No renderer-specific classification logic.
- No fuzzy or statistical classifier.

## Regression targets

- `Summer Chess Classes Learn & Play` remains a workshop.
- `Bluey's Big Stage Play` remains Art/Theater.
- `The Triple Nickel` becomes Lectures/Talks.
- Family movie listings become Art/Theater rather than Sports.
- Cake and wine pairing events become Food & Drink.
- Joshua Peace Saxxidelic and Englewood Heights remain music even when descriptions contain class language.
- A performer named Faith is not classified as Faith Based.
