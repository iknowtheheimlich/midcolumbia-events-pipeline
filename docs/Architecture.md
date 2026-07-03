# Mid-Columbia Events Pipeline Architecture

## Design Goals

- One canonical event schema.
- Source-specific logic isolated to adapters.
- Venue resolution performed once.
- Publishers consume normalized events only.
- Backwards-compatible schema evolution.

## Pipeline

```text
Source
   ↓
Harvester
   ↓
Parser
   ↓
Normalized Event Schema
   ↓
Venue Resolver
   ↓
Registry Optimizer
   ↓
Validation
   ↓
Publisher(s)
```

## Components

### Harvesters
Acquire raw HTML or source content. They never perform publishing logic.

### Parsers
Convert source-specific HTML into the shared event schema.

### Event Schema
The contract shared by every downstream component. Source adapters normalize into this schema.

### Venue Registry
Stores canonical venue identities and Google Place IDs.

### Registry Optimizer
Builds lookup tables from the registry for fast resolution.

### Resolver
Matches parsed venues to canonical registry entries. Unresolved venues are routed to the Unknown Venue Queue.

### Validation
Ensures schema integrity before publishing.

### Publishers
Generate Reddit, Notion, or future outputs without source-specific branching.

## Architectural Rules

1. One event schema.
2. One venue registry.
3. One resolver pipeline.
4. Publishers never parse HTML.
5. Harvesters never publish.
6. New sources plug in as adapters instead of modifying publishers.
7. Unknown data is quarantined rather than guessed.

This document should evolve only when architectural decisions change, not when implementation details change.