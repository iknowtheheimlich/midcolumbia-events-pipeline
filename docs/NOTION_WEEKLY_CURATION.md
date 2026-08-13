# Weekly Curation control surface

`Weekly Curation` is an opt-in operational control surface. Ordinary production does not sync or read it.

Identity is `SHA-256(v1 | publication week | case-folded source | source event ID | occurrence date)`. When the source ID is absent, the stable fallback replaces it with case-folded original title, original venue, and original time. Row number, ordering, Captain fields, category, target, and disposition never participate.

Pipeline-owned, Captain-owned, and derived properties are declared separately in `src/notion_weekly_curation.py`. Normal synchronization sends no Captain-owned properties, so Notion values survive every upsert. Duplicate keys, malformed Captain selects, and incomplete read-back are hard failures. Missing rows are retained; synchronization never deletes pages.

Notion's public API does not support creating or configuring database views. Operators must create `NEEDS REVIEW`, `ALL EVENTS`, `INCLUDED`, and `EXCLUDED` views in the Notion UI after review.
