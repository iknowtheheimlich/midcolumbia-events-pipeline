# Attempt 80 — Classification Confidence and Explainability

## Goal

Make category decisions measurable and reviewable without changing classification outcomes.

## Added fields

- `category_confidence`: existing score, normalized to `0.0–1.0`
- `category_reason`: existing classifier explanation
- `category_evidence`: structured evidence labels derived from the reason
- `category_confidence_band`: `high`, `medium`, `low`, or `none`
- `category_needs_review`: true for classified events below `0.75`

## Evidence labels

- `ExistingCategory`
- `SourceCategory`
- `TitleRule`
- `OrganizerHint`
- `VenueHint`
- `ContextRule`
- `VenueType`
- `DescriptionRule`
- `NoMatch`

## Review ordering

`sort_for_category_review()` orders events from lowest to highest confidence, with deterministic title and identity tie-breakers.

## Non-goals

Attempt 80 does not:

- alter category precedence
- combine competing signals
- recalibrate existing classifier scores
- automatically override or reject classifications
- change publisher output

This is an observational layer. Future calibration should use review outcomes and accumulated history rather than inventing confidence arithmetic without evidence.
