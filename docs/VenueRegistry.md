# Venue Registry

## Purpose

The Venue Registry is the canonical source of truth for physical event locations. Every resolved venue should map to a single registry entry regardless of how individual sources spell or format the venue name.

## Goals

- One canonical record per venue.
- Stable identifiers.
- Google Place ID as the primary external identity.
- Fast lookup through generated indexes.
- Human review for uncertain matches.

## Registry Pipeline

```text
Raw Venue
    ↓
Normalization
    ↓
Registry Lookup
    ↓
Exact Match
    ↓
Fuzzy Match
    ↓
Review Queue
    ↓
Canonical Venue
```

## Registry Fields

Each venue should maintain:

- Canonical Name
- Venue ID
- Google Place ID
- Address
- City
- State
- Latitude (optional)
- Longitude (optional)
- Known Aliases
- Status

## Status Values

- Active
- Pending Review
- Merged
- Retired

## Matching Rules

Priority:

1. Google Place ID
2. Registry ID
3. Exact canonical name
4. Known alias
5. High-confidence fuzzy match
6. Unknown Venue Queue

If confidence is insufficient, the venue is not resolved automatically.

## Unknown Venue Queue

Unknown venues are assets, not failures.

Each unknown venue should preserve:

- Original venue string
- Source
- Source URL
- Event title
- Date discovered

Nothing should be discarded because it cannot yet be resolved.

## Registry Optimizer

The Registry Optimizer generates read-only lookup tables used during parsing.

Responsibilities:

- Alias index
- Canonical name index
- Google Place ID index
- Normalized lookup tables

Source adapters consume these generated indexes rather than scanning the full registry.

## Governance Rules

- One venue record per physical location.
- Aliases belong to the canonical venue.
- Registry edits occur through review, not during parsing.
- Publishers never modify registry data.
- Source adapters never write registry entries.

## Current State

Current registry contains approximately 1,056 venues with Google Place IDs.

Attempt_14 established the Registry Optimizer as the performance layer above the registry.

Attempt_15 and beyond should reuse the registry rather than introducing source-specific venue handling.