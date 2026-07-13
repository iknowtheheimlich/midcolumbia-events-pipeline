# Attempt_43 Occurrence Resolution

## Purpose

Resolve multiple source records that describe the same real-world occurrence before Program Intelligence groups legitimate sibling sessions.

## Evidence

- Same calendar date is mandatory.
- Shared source/external URL or Eventbrite ID is conclusive.
- Otherwise resolution requires canonical venue identity, start times within ten minutes, and strong normalized-title similarity.
- Different venues or materially different start times remain separate occurrences.

## Merge policy

The source registry priority selects the primary record. All source names, URLs, and compact source-event provenance are preserved. The additive intelligence contract records resolution confidence and evidence.

## Compatibility

The existing pipeline fields `deduplicated_publisher_ready_events`, `duplicate_groups`, and `skipped_low_quality_dedupe` remain unchanged. The implementation behind them now resolves occurrences rather than relying only on exact tuple equality.
