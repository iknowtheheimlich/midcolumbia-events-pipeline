# Attempt_24_Eventbrite_Bridge

## Decision

Do not add Eventbrite as a direct active adapter.

## Evidence

Direct access was tested through both plain HTTP and Playwright/Chromium.

Both approaches returned:

- HTTP 405
- `Human Verification`
- no event cards
- no JSON-LD
- no `__NEXT_DATA__`
- no useful API responses

This makes direct Eventbrite harvesting too brittle for the production pipeline.

## Coverage analysis

The existing live harvest was scanned for Eventbrite links already exposed by trusted local sources.

Observed sample:

- normalized events scanned: 598
- unique Eventbrite links found: 7
- all 7 arrived through `VisitTriCities`

Direct Eventbrite harvesting would therefore add very little marginal coverage while introducing a bot-wall dependency.

## Implemented bridge

Attempt_24 adds an Eventbrite bridge instead of an adapter.

The bridge:

- scans harvested normalized events
- detects Eventbrite URLs in `url` and `external_url`
- extracts Eventbrite event IDs
- deduplicates reposted Eventbrite links
- writes a review queue under `generated/eventbrite_bridge/`

Run:

```powershell
python -m tools.harvest_all
python -m tools.report_eventbrite_bridge
```

## Pipeline boundary

Eventbrite is not registered in `AVAILABLE_ADAPTERS` and does not participate as an independent source.

Existing trusted local sources remain responsible for locality, venue, and event normalization. The bridge preserves Eventbrite identity only for review and coverage analysis.

## Revisit criteria

Reconsider a direct Eventbrite adapter only if one of these becomes true:

- Eventbrite restores a stable public API or feed
- authenticated API access becomes available
- local Eventbrite-only coverage rises materially above inherited coverage
- a trusted third-party feed exposes Eventbrite inventory without a bot-wall dependency

Until then, the bridge is the correct engineering tradeoff.
