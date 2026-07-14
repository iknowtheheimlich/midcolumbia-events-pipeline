# Attempt 59 — AllEvents Structured API

## Problem

The AllEvents city-page HTML and embedded JSON-LD did not contain the complete date-filtered inventory shown in the browser. Production could report a healthy harvest while missing events that users could plainly see in the AllEvents day view.

Browser HAR captures identified the structured endpoint used by that day view:

`POST https://allevents.in/api/index.php/events/web/qs/search_with_filters`

## Implementation

- Query the structured endpoint for each publication date.
- Cover Kennewick, Richland, Pasco, West Richland, and Prosser.
- Do not seed Hermiston.
- Normalize structured event IDs, local timestamps, venue data, descriptions, images, recurrence metadata, ticket URLs, and prices into the existing canonical event shape.
- Deduplicate overlap across city queries by event ID and occurrence time.
- Preserve generated raw responses under `generated/harvest/AllEvents/`.
- Route the production AllEvents slot through the API collector.
- Retain the existing HTML/JSON-LD parser for fixture compatibility and fallback investigation.

## Boundaries

- No opaque browser-session URLs or cookies are persisted.
- No browser automation dependency is introduced.
- No downstream publisher contract changes are required.
- Geographic intelligence remains responsible for final local/regional scope decisions.

## Expected impact

AllEvents production inventory should now match the structured date results used by the website rather than the smaller static city-page inventory.
