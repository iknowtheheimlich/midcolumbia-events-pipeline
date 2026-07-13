# Attempt_41 Program Intelligence

Introduces a publisher-facing distinction between a program and its occurrences.

## Behavior

- Existing editorial-event queues remain available.
- Same-day sibling occurrences are grouped only when cleaned title, semantic category,
  publication target, and source all match.
- Every occurrence preserves date, time, venue, city, source identifier, and URL.
- Single occurrences retain the existing Reddit line contract.
- Multiple occurrences render as a compact chain.
- Same-venue programs compress the venue and list times.
- Multi-venue programs list linked venue/time pairs.

## Non-goals

- No fuzzy cross-source deduplication.
- No recurrence-series grouping across calendar days.
- No canonical-event schema replacement.
- No time-sentinel cleanup.

These remain separate intelligence milestones.
