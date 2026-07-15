# Attempt 74 — Venue Intelligence Discovery

## Goal

Discover explainable venue-level category priors from accumulated classified event history without automatically changing the active venue category registry.

## Inputs

The discovery engine consumes one or more JSON files, JSONL files, or directories containing canonical event dictionaries with:

- canonical venue or venue registry name
- final category
- optional venue type
- optional event date

Rows missing venue or category are ignored.

A single weekly publisher snapshot is valid for a smoke test but is not sufficient evidence for promotion. Production discovery should run against accumulated historical exports or an archive directory spanning many runs.

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

Excluded venue types are detected from registry metadata first. When metadata is absent, conservative name patterns identify obvious wineries, breweries, bars, restaurants, hotels, parks, fairgrounds, and similar multipurpose venues.

## Recommendations

`PROMOTE`

The venue meets all deterministic promotion thresholds.

`REVIEW`

Reserved for evidence that is sufficient in volume but requires a human decision. Attempt 74 does not currently emit this state automatically.

`INSUFFICIENT`

The venue does not yet have enough classified historical events. This is not a judgment about venue stability.

`REJECT`

The venue is an excluded multipurpose type or fails purity, second-category, or entropy thresholds.

## Confidence

Confidence combines:

- dominant category purity
- conservative sample-size factor: `n / (n + 20)`
- entropy-derived stability

Sample size dominates early evidence. One pure observation is approximately 0.048 confidence; five are 0.20; 25 are approximately 0.56; 100 are approximately 0.83 before purity or entropy penalties.

Confidence is explanatory metadata. Promotion eligibility remains governed by the explicit thresholds above.

## Outputs

Run against one accumulated history file:

```powershell
python -m tools.report_venue_intelligence history/canonical_events.jsonl
```

Run against multiple exports or an archive directory:

```powershell
python -m tools.report_venue_intelligence history/2026-Q1 history/2026-Q2.json fixtures/archive.jsonl
```

Default artifacts:

```text
artifacts/venue_intelligence_candidates.json
artifacts/venue_intelligence_report.txt
```

The text report includes input count, historical event count, and separate Promote, Review, Insufficient Evidence, and Reject sections.

## Safety boundary

Attempt 74 never writes to:

```text
config/venue_category_hints.json
```

Candidate approval and registry promotion remain explicit human actions.

## Tests

Regression coverage verifies:

- pure venues are promoted only with sufficient history
- small samples are marked insufficient
- tiny samples remain low-confidence
- confidence increases with sample size
- excluded venue types are rejected from metadata or conservative name inference
- mixed venues are rejected
- incomplete rows are ignored
- canonical registry names group aliases
- output ordering is deterministic
