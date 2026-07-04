# Algolia Adapter

## Purpose

Shared adapter utilities for sources backed by Algolia search indexes.

Visit Tri-Cities uses Algolia for event listings, so Attempt_15 should treat the site as a structured search-index source rather than a DOM scrape target.

## Source Pattern

Typical Algolia multi-query endpoint:

```text
https://<APP_ID>-dsn.algolia.net/1/indexes/*/queries
```

The request payload includes one or more requests:

```json
{
  "requests": [
    {
      "indexName": "prod-visit-tri-cities-2024-listings",
      "params": "..."
    }
  ]
}
```

## Visit Tri-Cities Current Values

```text
APP_ID:   EYQHJ2IY2M
INDEX:    prod-visit-tri-cities-2024-listings
```

The public browser search key is intentionally not treated as a secret because it is shipped to visitors by the site.

## Design Rule

The generic Algolia layer should handle:

- Payload shape extraction
- Hit extraction
- Pagination support
- Basic request contract

Source-specific config should handle:

- App ID
- Index name
- Filters
- Source name
- Source-specific normalization quirks

## Boundary

Algolia utilities do not resolve venues, publish Reddit Markdown, or modify the Venue Registry.
