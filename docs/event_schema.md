# Event Schema

The canonical event object is `EventRecord` in `src/cargo_harvester/models.py`.

Every source adapter must output this shape, even if some fields are blank.

## Fields

| Field | Purpose |
|---|---|
| `event_name` | Display title for the event. Fatal if missing. |
| `date_raw` | Human-readable or source-provided date. Fatal if missing. |
| `start_time` | Start time when available. Nonfatal if missing. |
| `end_time` | End time when available. |
| `venue` | Venue/location name. Nonfatal if missing. |
| `city` | City label used for sorting/filtering. |
| `address` | Full address when available. |
| `source` | Source name, such as `AllEvents`. |
| `source_url` | Original event URL. Fatal if missing. |
| `category` | Category/tag from source or inferred later. |
| `cost` | Cost/free text when available. |
| `description` | Source description or rendered card text. |
| `image_url` | Thumbnail/cover URL. Nonfatal if missing. |
| `harvest_date` | Date used during the sweep. Useful for debugging. |
| `harvest_url` | URL used to obtain the record. Useful for debugging. |
| `status` | Workflow state: Raw, Reviewed, Ready, Posted, Excluded. |
| `reddit_include` | Yes/No flag for Reddit output. |
| `needs_review` | Yes/No flag for imperfect rows. |
| `review_notes` | Semicolon-separated review warnings. |
| `dedupe_key` | Normalized key for duplicate removal. |

## Fatal vs nonfatal

Fatal records are skipped by outputs that require usable events.

Fatal:

- Missing event name
- Missing date
- Missing source URL

Nonfatal:

- Missing start time
- Missing venue
- Missing image URL

Nonfatal rows may still be useful in Reddit or Notion if the event is otherwise identifiable.

## Dedupe key

The current dedupe key uses:

```text
event_name | date_raw | start_time | venue | city | source_url
```

This is intentionally conservative. Cross-source dedupe will need a smarter key later because two sources may point to different URLs for the same event.

## Future improvements

- Parsed ISO date field
- Parsed start/end datetime fields
- Confidence score
- Venue normalization table
- Source priority ranking
- Cross-source duplicate groups
