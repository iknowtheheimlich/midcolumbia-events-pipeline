# Attempt 74 — Venue Intelligence Discovery

## Goal

Discover explainable venue-level category priors from classified event history without automatically changing the active venue category registry.

## Inputs

The discovery engine consumes canonical event dictionaries containing:

- canonical venue or venue registry name
- final category
- optional venue type
- optional event date

Rows missing venue or category are ignored.

## Promotion contract

Default promotion criteria:

- at least 25 classified events
- dominant category at least 90 percent
- second category no more than 10 percent
- normalized category entropy no more than 0.55
- venue type is not inherently multipurpose

Default excluded venue types:

- bars
- breweries
- community centers
- convention centers
- fairgrounds
- hotels
- parks
- restaurants
- wineries

Excluded venue types are rejected even when the currently observed sample appears pure. A short time window should not convert a multipurpose venue into a false prior.

## Recommendations

`PROMOTE`

The venue meets all deterministic promotion thresholds.

`REVIEW`

The venue has insufficient sample size. The engine does not treat small samples as proof of instability.

`REJECT`

The venue is an excluded multipurpose type or fails purity, second-category, or entropy thresholds.

## Confidence

Confidence combines:

- dominant category purity
- sample-size factor, capped at 100 events
- entropy-derived stability

Confidence is explanatory metadata. Promotion eligibility remains governed by the explicit thresholds above.

## Outputs

Run:

```powershell
python -m tools.report_venue_intelligence fixtures/real_multi_source/deduplicated_publisher_ready_events.json
```

Default artifacts:

```text
artifacts/venue_intelligence_candidates.json
artifacts/venue_intelligence_report.txt
```

The JSON file is suitable for review tooling. The text report groups venues into Promote, Review, and Reject sections.

## Safety boundary

Attempt 74 never writes to:

```text
config/venue_category_hints.json
```

Candidate approval and registry promotion remain explicit human actions.

## Tests

Regression coverage verifies:

- pure venues are promoted
- small samples remain review candidates
- excluded multipurpose venue types are rejected
- mixed venues are rejected
- incomplete rows are ignored
- canonical registry names group aliases
- output ordering is deterministic
