# Attempt_40 Editorial Style Intelligence

Purpose: derive clean Reddit-facing titles and venues without mutating canonical event identity.

## Contract

- Canonical `title` and venue identity remain available upstream.
- Editorial events carry the cleaned title plus `canonical_title` and `style_reason`.
- Known raw addresses may map to curated venue names through `config/editorial_style.json`.
- Unknown addresses are compacted to the street-address portion rather than publishing city/state/country duplication.
- Configured title prefixes and terminal dates are removed from display titles.
- A terminal `at <venue>` or `@ <venue>` is removed when the venue is rendered separately.
- Renderers remain presentation-only consumers.

Example:

```text
Summer Thursdays at Columbia Gardens |
325 East Columbia Gardens Way, Kennewick, WA, United States, Washington 99336, Kennewick |
6-11:59p
```

becomes:

```text
Summer Thursdays | Columbia Gardens, Kennewick | 6-11:59p
```

Time semantics are intentionally deferred to a separate milestone.
