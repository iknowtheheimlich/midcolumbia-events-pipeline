# Attempt_14_Registry_Optimizer Verification

## Purpose

This document defines the verification checklist for locking `Attempt_14_Registry_Optimizer` before beginning `Attempt_15_Visit_Tri-Cities`.

Attempt_14 is not considered fully locked until the optimizer output, resolver integration, publisher behavior, and unknown venue queue are verified against known-good input.

## Verification Scope

Verify that the Registry Optimizer:

- Reads the Venue Registry successfully.
- Generates lookup tables deterministically.
- Preserves Google Place ID mappings.
- Preserves canonical venue names.
- Preserves aliases.
- Does not mutate the source Venue Registry.
- Produces lookup output usable by the resolver.

## Expected Optimizer Outputs

The optimizer should generate read-only lookup structures for:

- Canonical venue names
- Normalized venue keys
- Known aliases
- Google Place IDs
- Registry IDs, if present

Exact filenames may vary by implementation, but the generated artifacts should be documented once confirmed.

## Required Checks

### 1. Registry Load Check

Confirm the optimizer can load the current Venue Registry without errors.

Expected result:

- Registry loads successfully.
- Venue count is approximately 1,056 records.
- Google Place ID coverage is preserved.

### 2. Deterministic Output Check

Run the optimizer twice against the same registry input.

Expected result:

- Generated lookup output is identical across runs.
- No timestamp-only noise appears in committed lookup artifacts unless intentionally excluded from comparison.

### 3. Canonical Name Lookup Check

Choose several known venues and confirm canonical lookup works.

Example venue categories:

- Civic venues
- Libraries
- Parks
- Schools
- Wineries/breweries
- Community centers

Expected result:

- Known canonical venue names resolve to the correct registry records.

### 4. Alias Lookup Check

Choose known aliases and confirm they resolve to canonical venue records.

Expected result:

- Alias matches resolve to canonical names.
- Alias matches preserve original raw venue text on the event object.

### 5. Google Place ID Lookup Check

Choose known Google Place IDs and confirm direct lookup works.

Expected result:

- Google Place ID resolves to the correct canonical venue.
- No duplicate Google Place ID conflicts exist unless explicitly documented for review.

### 6. Resolver Integration Check

Run representative saved HTML through the full pipeline.

Expected result:

- Resolver consumes optimizer-generated lookup tables.
- Known venues resolve correctly.
- Unknown venues route to the Unknown Venue Queue.
- Publisher output remains chronological.

### 7. Unknown Venue Queue Check

Feed at least one intentionally unknown venue.

Expected result:

- Unknown venue is not guessed.
- Unknown venue appears in the review queue.
- Original venue string, source, event title, URL, and date are preserved.

### 8. Publisher Regression Check

Run the Reddit Publisher against known-good normalized events.

Expected result:

- Output remains chronological.
- Markdown formatting is unchanged unless intentionally updated.
- Unknown venues do not pollute the main published output.

## Lock Criteria

Attempt_14 may be considered locked when:

- Optimizer output is deterministic.
- Resolver uses optimizer output successfully.
- Venue matches remain accurate.
- Unknown venue routing remains clean.
- Publisher output remains stable.
- Any generated lookup artifacts are documented.

## Failure Handling

If verification fails:

1. Do not begin Attempt_15.
2. Capture the failing input.
3. Capture expected vs actual behavior.
4. Fix optimizer/resolver behavior.
5. Re-run the full checklist.

## Notes for Attempt_15

`Attempt_15_Visit_Tri-Cities` should not introduce new venue resolution behavior.

It should rely on:

- Existing event schema
- Existing Venue Registry
- Existing Registry Optimizer outputs
- Existing Resolver Pipeline
- Existing Unknown Venue Queue

If Visit Tri-Cities exposes new venue edge cases, those should be routed through review rather than handled as source-specific exceptions.