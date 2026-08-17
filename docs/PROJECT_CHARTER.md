# Mid-Columbia Mission Control — Project Charter

## Mission

Maintain a definitive, curated, and auditable knowledge system for public Mid-Columbia events.

**Operational flow:** Discover → Curate → Verify → Publish

## Purpose

Mid-Columbia Mission Control discovers events from public sources, normalizes and enriches them, resolves them against curated knowledge, surfaces uncertainty for human review, and publishes trustworthy outputs. Reddit is the first publisher, not the boundary of the system.

## Principles

1. **Canonical knowledge is human-curated.** Ultimate Venues, Hosts, Artists, recurring records, and future entity registries own presentation and identity.
2. **Harvesters discover; they do not define truth.** Source data may propose facts but must not silently overwrite curated records.
3. **Every inference must be explainable.** Confidence, provenance, and reasons travel with inferred fields.
4. **No silent mutation.** Review candidates are clearly flagged and require deliberate promotion into canonical knowledge.
5. **Publishing is deterministic.** The same canonical inputs and mission profile should produce the same output.
6. **Mission Control is the launch authority.** A run may generate artifacts while still being held for review.
7. **History teaches the system.** The Mission Archive improves aliases, recurring-pattern knowledge, confidence tuning, and Reference Missions without becoming a hidden live-publishing dependency.
8. **Direct links remain visible.** Canonical URLs are normalized, not obscured by link shorteners.
9. **Failures remain inspectable.** Flight Recorder artifacts preserve source health, counts, warnings, review state, regression state, and launch decisions.
10. **Architecture stays separated.** Harvest, knowledge, review, mission control, and publishing may cooperate but do not collapse into one layer.

## Architecture

```text
Harvest Bay
    ↓
Normalization
    ↓
Knowledge Core
    ↓
Review Console
    ↓
Mission Control
    ↓
Publishers
```

## Core Systems

- **Harvest Bay:** Public source acquisition and source-health telemetry.
- **Knowledge Core:** Canonical entities, aliases, relationships, provenance, historical corpus, and recurring patterns.
- **Review Console:** Human decisions for unresolved or low-confidence knowledge.
- **Flight Recorder:** Immutable mission-level operational telemetry.
- **Mission Control:** Launch readiness, warnings, trends, and Captain's Console summary.
- **Mission Profile:** Publisher routing, vocabulary, formatting, and launch policy.
- **Reference Missions:** Frozen real-world missions used for product-level regression testing.

## Success Measures

The system succeeds when:

- weekly publication is predictable and auditable;
- canonical knowledge coverage improves over time;
- the review backlog remains understandable and actionable;
- corrections made once improve future missions;
- source failures and unusual changes are visible before publication;
- new publishers can consume canonical knowledge without duplicating harvest or curation logic.

## Non-Goals

- Automatically promoting uncertain entities into canonical registries.
- Allowing source-specific presentation to override curated metadata.
- Using opaque AI confidence without provenance or reasons.
- Making Reddit formatting concerns part of the knowledge core.

## Project Identity

**Name:** Mid-Columbia Mission Control  
**Mission prefix:** `MC`  
**Mission ID format:** `MC-YYYY-WWW`, where `WWW` is the zero-padded ISO mission week.  
**Example:** Week beginning July 13, 2026 → `MC-2026-029`
