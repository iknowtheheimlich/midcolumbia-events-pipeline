# Attempt_51_ParserHygiene

## Objective

Repair malformed source text at the adapter boundary instead of teaching editorial or
rendering layers to compensate for parser damage.

## Initial defect

Richland Library LibCal anchors can contain the visible title alongside accessibility
fragments. Blindly concatenating every text node produced output such as:

```text
Family Movies ofFamily Movies of the 1990s: ... the
```

## Implementation

The Richland Library parser now:

- normalizes individual anchor text fragments;
- prefers the longest fragment when shorter fragments are already contained within it;
- discards redundant one- and two-word accessibility fragments;
- preserves genuinely independent title fragments in document order;
- retains flattened duplicate-prefix repair for legacy input;
- decodes HTML entities, nonbreaking spaces, and zero-width spaces.

## Boundary

This is source-specific parsing behavior. Canonical title identity, occurrence resolution,
editorial style, and rendering contracts are unchanged.

## Regression safety

Tests cover the observed Family Movies defect, independent split titles, entity decoding,
popover separation, and existing LibCal event extraction.
