# Mid-Columbia Event Intelligence — Vision

## Purpose

Build a reproducible regional event intelligence system that turns scattered public event listings into trustworthy, connected knowledge.

The weekly Reddit post is the first production output, not the final boundary of the system.

## Closed-loop architecture

Every item should have a traceable path:

1. Source discovery
2. Raw capture
3. Adapter normalization
4. Text and venue normalization
5. Geographic and editorial classification
6. Content-quality screening
7. Deduplication and recurrence review
8. Publisher output
9. Audit reports and maintenance queues
10. Registry and knowledge updates that improve the next run

No silent drops. No untraceable corrections. Review queues close the loop when automation cannot decide safely.

## Production track

The production track exists to generate the weekly community-events list reliably and with minimal manual repair.

It includes:

- live source harvesting
- canonical event schema
- encoding repair
- venue resolution
- geographic intelligence
- junk-content rejection
- recurrence handling
- deduplication
- Reddit publishing
- regression fixtures and reports

Production changes must improve reliability, reduce manual work, or improve the published list.

## Knowledge track

The knowledge track models the region itself:

- venues and aliases
- organizations and branches
- performers and hosts
- event series
- geography and editorial scope
- source provenance
- observation history
- relationships among entities

The knowledge layer should support many outputs without making any one external platform the core database.

## Outputs

The canonical pipeline may eventually feed:

- Reddit weekly posts
- Notion views and maintenance queues
- SITREP summaries
- analytics and trend reports
- maps and calendars
- Home Assistant or Discord integrations
- future searchable applications or APIs

Notion is a consumer and editorial workspace. It is not a hard runtime dependency for harvesting or publishing.

## Design principles

- Preserve provenance.
- Prefer deterministic rules over fuzzy guesses.
- Keep reviewable uncertainty instead of hiding it.
- Protect golden fixtures from live runs.
- Keep generated artifacts separate from source-controlled truth.
- Reuse authoritative registries rather than creating competing copies.
- Make every improvement measurable with tests and reports.
- Build closed loops: each report should lead to a correction that reduces future work.
