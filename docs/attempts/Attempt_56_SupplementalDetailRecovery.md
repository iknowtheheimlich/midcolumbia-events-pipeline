# Attempt_56_SupplementalDetailRecovery

## Objective

Recover useful event details that AllEvents exposes in descriptive text instead of its structured price or time fields, while preserving canonical event-time semantics.

## Scope

Attempt 56 adds conservative recovery for:

- free-admission language
- explicit dollar prices and ranges
- labeled schedule assignments such as doors, opening acts, headliners, sessions, or hourly activities

Recovered schedule assignments are supplemental metadata. They never replace `start_time` or `end_time`.

## Recovery Contract

Structured fields remain authoritative.

```text
structured cost
    -> keep unchanged
missing structured cost + reliable description match
    -> recover cost with provenance

canonical start/end time
    -> keep unchanged
labeled times in description
    -> store as schedule_items
bare unlabeled time
    -> ignore
```

Recovered fields carry explicit provenance:

- `cost_source: description`
- `schedule_source: description`
- intelligence reasons and confidence values

## Production Artifact

Normal production writes:

```text
artifacts/reddit/Supplemental_Details.txt
```

The report contains only weekly events with description-recovered details. Events that merely possess already-structured prices are omitted, keeping the artifact exception-focused.

When harvest health is degraded, the supplemental report follows the existing degraded-artifact routing and does not overwrite the normal production artifact.

## Publishing Boundary

Attempt 56 does not automatically append recovered details to Reddit event lines. The report exposes real recovered data first so presentation rules can be based on observed cases rather than speculative formatting.

## Validation

Coverage includes:

- free price recovery
- numeric price recovery
- structured-cost precedence
- labeled schedule extraction
- bare-time rejection
- canonical time preservation
- weekly filtering
- omission of structured-only prices
- human-readable report rendering
