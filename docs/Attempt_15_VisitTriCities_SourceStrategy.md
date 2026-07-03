# Attempt_15 Visit Tri-Cities Source Strategy

## Problem

The Visit Tri-Cities events page does not expose event listings in ordinary static HTML.

The public page shell renders the message:

```text
Please enable JavaScript to show the Event Listings listings.
```

That means the usable event data is injected client-side.

The uploaded saved asset folder contained site assets and JavaScript, but not a rendered event listing payload.

## Observed Assets

The uploaded `Visit Tri-Cities_files.zip` contained files such as:

- `calendar-widget.js.download`
- `main.min.1770658109.js.download`
- CSS files
- SVG/image assets
- empty tracking/script placeholder files

The most useful file was:

```text
calendar-widget.js.download
```

That file appears to call Seeker calendar endpoints, including event search endpoints under:

```text
https://api.seeker.io/calendars/{calendarId}/events/search
https://api.seeker.io/calendars/{calendarId}/events/search/minimal
```

## Strategy

Do not scrape rendered DOM first.

Preferred approach:

1. Identify the Visit Tri-Cities calendar ID.
2. Fetch event data directly from the Seeker API endpoint.
3. Save the API response as a fixture.
4. Normalize API event objects into the canonical event schema.
5. Pass venues through the existing resolver.
6. Preserve source URLs and raw venue strings.

## Why This Approach

The site is JavaScript-rendered and fragile as a DOM scraping target.

API-first parsing should be more stable than trying to scrape generated HTML after scripts execute.

DOM scraping should be treated as a fallback only if the API endpoint cannot be used reliably.

## Fixture Update

The current placeholder files are:

```text
fixtures/visit_tricities/saved_page.html
fixtures/visit_tricities/expected_events.json
```

Because Visit Tri-Cities appears API-backed, the fixture set should likely expand to:

```text
fixtures/visit_tricities/api_events_search.json
fixtures/visit_tricities/expected_events.json
```

The original `saved_page.html` can remain as a capture note or page-shell fixture.

## Open Questions

- What is the Visit Tri-Cities Seeker `calendarId`?
- Is the API endpoint public and stable without browser session headers?
- Does the search endpoint include full venue/address details?
- Are recurring events expanded into instances, or does the adapter need to call an instances endpoint?

## Next Step

Use the browser network panel on the Visit Tri-Cities events page and inspect XHR/fetch calls.

Look for requests to:

```text
api.seeker.io
```

Capture:

- Full request URL
- Calendar ID
- Query parameters
- JSON response sample

Once captured, save the response as:

```text
fixtures/visit_tricities/api_events_search.json
```

Then implement the adapter against the JSON fixture instead of against rendered HTML.
