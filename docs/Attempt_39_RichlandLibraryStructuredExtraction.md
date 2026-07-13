# Attempt_39_RichlandLibraryStructuredExtraction

Objective: repair Richland Library event extraction at the collector boundary.

Changes:
- parse LibCal event anchors with `HTMLParser` rather than an opening-tag regex
- keep popover metadata out of event titles
- preserve description, audience, presenter, and date/time fields separately
- repair immediately duplicated accessibility-title prefixes
- ignore non-event links such as telephone anchors

The canonical event schema and every downstream publisher contract remain unchanged.
No renderer cleanup or source-specific publisher rule was added.
