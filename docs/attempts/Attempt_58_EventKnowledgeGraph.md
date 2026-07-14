# Attempt_58_EventKnowledgeGraph

## Objective

Create an additive, provenance-backed relationship index from the enriched event model without changing publisher behavior or introducing a graph database dependency.

## Artifact

Production writes:

```text
artifacts/intelligence/Event_Knowledge_Graph.json
```

Degraded harvests route the artifact through the existing degraded-output policy.

## Node types

- `EVENT`
- `VENUE`
- `ORGANIZATION`
- `SERIES`
- `TICKET_PROVIDER`

## Edge types

- `HOSTED_AT`
- `ORGANIZED_BY`
- `PART_OF_SERIES`
- `TICKETED_BY`

## Evidence policy

Relationships are emitted only from explicit canonical fields.

The graph does not infer performers, sponsors, ownership, or series membership from descriptive prose. Those relationships require a future evidence model and focused regression cases.

Every edge preserves source, source event ID, and source URL when available.

## Identity policy

- Event identity uses source plus source event ID when available.
- URL is the next event identity fallback.
- Venue Registry IDs are authoritative for venue identity.
- Unresolved venues use normalized venue and city.
- Organization, series, and ticket-provider IDs are deterministic hashes of explicit identity values.

## Boundary

This milestone does not:

- alter Reddit output
- replace the canonical event model
- add a graph database
- infer relationships from prose
- perform historical anomaly detection
- create field-level source fusion

The artifact establishes a stable relationship contract. Behavioral modeling should only follow when the graph demonstrates recurring operational value.
