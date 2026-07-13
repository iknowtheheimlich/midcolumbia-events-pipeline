# Attempt_49_OccurrenceResolutionTuning

Tune cross-source occurrence identity without changing the legacy exact-deduplication contract.

## Goals

- Preserve exact URL and Eventbrite matches as conclusive evidence.
- Compare canonical venue IDs, registry names, parent venues, and normalized venue aliases.
- Tolerate promotional title suffixes and small typographical differences.
- Require the same date and near-identical start time for non-conclusive matches.
- Preserve provenance and source-priority primary selection.
- Reject same-title events at different venues or materially different times.

## Production order

1. Legacy exact deduplication
2. Cross-source occurrence resolution
3. Program grouping

## Guardrails

Venue matching is required before fuzzy title evidence is considered. Missing start times do not add positive evidence. Separate sessions and unrelated generic titles remain separate occurrences.
