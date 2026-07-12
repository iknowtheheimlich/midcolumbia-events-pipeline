# Attempt_37_AllEventsCollector

## Objective

Add AllEvents as a first-class collector without changing downstream intelligence or publication code.

## Acquisition

The collector requests the AllEvents listing pages for Kennewick, Pasco, Richland, and West Richland. The raw artifact is stored as a JSON object keyed by city because one harvest contains multiple HTML documents.

## Normalization

Only embedded Schema.org JSON-LD event nodes are normalized. Recommendation prose, FAQ content, navigation, and visible-card boilerplate are not parsed.

Normalized fields include title, description, dates, times, venue, address, city, state, organizer, source URL, source event ID, image URL, status, attendance mode, and the original AllEvents category as `source_category`.

The collector does not map AllEvents categories into the pipeline's semantic category vocabulary. That remains an intelligence-layer responsibility.

## Duplicate handling

The collector removes exact repeated listing URLs encountered across multiple city pages. Cross-source and fuzzy duplicates remain the responsibility of the shared deduplication layer.

## Failure behavior

If live acquisition fails and the normalized fixture exists, harvest infrastructure reuses the fixture and records a source warning. An AllEvents outage therefore degrades freshness rather than aborting the entire production run.

## Boundaries

No publisher, editorial, venue-registry, geography, screening, or deduplication behavior changed in this attempt.
