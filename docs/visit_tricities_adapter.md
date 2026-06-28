# Visit Tri-Cities Adapter

## Current finding

The Visit Tri-Cities events page is JavaScript-driven. The static HTML includes this message:

```text
Please enable JavaScript to show the Event Listings listings.
```

That means a static requests/HTML parser will not see event records. The adapter uses Playwright to render the page before extracting cards.

## Current implementation

```text
src/cargo_harvester/sources/visit_tricities.py
```

The adapter:

- Opens `https://www.visittri-cities.com/events/`.
- Waits for JavaScript-rendered content.
- Scrolls the page.
- Finds event-looking links under `/events/`.
- Walks up to card-like containers.
- Extracts text, event URL, and image URL.
- Converts each card to `EventRecord`.

## CLI usage

```cmd
python -m cargo_harvester.cli --city kennewick --start 2026-07-01 --end 2026-07-07 --output output --visit-tricities
```

## Limitations

This is a first rendered-card adapter, not the final scraper.

Known limitations:

- Date filtering is not confirmed yet.
- The page controls its own search/filter UI.
- A stable backend/API endpoint has not yet been identified.
- Records may need review because rendered cards may omit time, venue, or city.

## Next steps

1. Run locally with `--visible --visit-tricities`.
2. Inspect `output/unified_events.csv` for field quality.
3. If counts/fields are poor, use browser dev tools to identify the listing API endpoint.
4. Replace rendered-card extraction with the API endpoint if found.

## Engineering note

This adapter is intentionally conservative. It is better to return review-marked records than fake clean data.
