# Attempt 75 — Organizer Category Intelligence

## Goal

Add organizer-level category priors that travel across venues without overriding stronger event evidence.

## Precedence

1. Explicit title rules
2. Existing or mapped source category
3. General title rules
4. Organizer category hint
5. Venue category hint
6. Venue context and venue type
7. Description evidence
8. Review queue

Organizer evidence precedes venue evidence because organizers commonly move between locations while venues frequently host mixed programming.

## Registry

Organizer hints are stored in:

```text
config/organizer_category_hints.json
```

Each record may contain:

```json
{
  "aliases": ["Master Gardeners"],
  "category_hint": "Classes/Workshops",
  "category_confidence": 0.94,
  "hint_strength": "strong"
}
```

Initial promoted organizers:

- WSU Extension Master Gardeners → Classes/Workshops
- Tri-City Dust Devils → Sports
- B Reactor Museum Association → Lectures/Talks
- WSU Tri-Cities → Lectures/Talks, soft hint

## Behavior

Examples:

- Plant Clinic by Master Gardeners at Richland Public Library → Classes/Workshops
- Plant Clinic by Master Gardeners at REACH Museum → Classes/Workshops
- Annual Charity Fundraiser by Master Gardeners → Fundraisers
- First Pitch Friday by Tri-City Dust Devils → Sports

The organizer supplies a prior. It does not make the final decision when explicit title or source-category evidence exists.

## Explainability

Organizer decisions emit reasons such as:

```text
organizer_hint=WSU Extension Master Gardeners;strength=strong
```

## Scope boundary

Attempt 75 consumes a manually approved organizer registry. Automatic organizer discovery is deferred until organizer fields and aliases have enough historical coverage to support reliable statistics.
