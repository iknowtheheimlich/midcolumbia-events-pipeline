# Mid-Columbia Mission Control — Mission Operations Manual

## Mission

Mid-Columbia Mission Control discovers, curates, verifies, and publishes reliable public-event information for the Mid-Columbia region.

Mission flow:

`Discover → Curate → Verify → Publish`

The publisher is not the authority on readiness. Mission Control records the run and determines whether the mission is ready to publish or must be held for review.

## Operating principles

- Human-curated canonical knowledge is authoritative.
- Ultimate Venues owns venue presentation and destination links.
- Hosts and Artists own their canonical names and official links.
- Harvesters discover events; they do not overwrite curated registries.
- Missing or uncertain knowledge is surfaced for review.
- No review workflow silently promotes or mutates canonical records.
- Every production run writes stable latest artifacts and a timestamped archive.
- Improvements begin with observed mission results, not speculative formatting changes.

## Repository systems

- `adapters/` — live source harvesting and normalization.
- `src/` — canonical pipeline, knowledge, editorial, review, and Mission Control logic.
- `tools/` — operator commands.
- `generated/corpus/` — knowledge artifacts learned from the historical Mission Archive.
- `artifacts/reddit/` — rendered Main and Community Reddit posts.
- `artifacts/mission_control/latest/` — stable current dashboard and Flight Recorder.
- `artifacts/mission_control/archive/` — immutable timestamped mission records.
- `docs/` — charter, operations, release checklist, and logbook.

## Mission IDs

The mission ID is deterministic from the publication week using the ISO week number.

Example:

- Week beginning July 13, 2026: `MC-2026-029`
- Week beginning July 20, 2026: `MC-2026-030`

A repeated run for the same week keeps the same Mission ID but receives a distinct timestamped archive directory.

## Standard launch sequence

### 1. Synchronize the branch

```powershell
git pull origin hotfix-v1.0.1-reddit-categories
```

### 2. Run regression tests

```powershell
python -m pytest -q
```

Do not continue with a known regression failure.

### 3. Build the Knowledge Core when the historical database changed

```powershell
python -m tools.build_knowledge_base `
  --historical-corpus "<actual path to the full Reddit database CSV>"
```

Expected artifacts:

- `generated/corpus/venues.json`
- `generated/corpus/hosts.json`
- `generated/corpus/artist_candidates.json`
- `generated/corpus/recurring_patterns.json`
- `generated/corpus/summary.json`

The historical corpus proposes knowledge. It does not overwrite the curated Notion registries.

### 4. Run the weekly production mission

CSV fallback:

```powershell
python -m tools.publish_reddit_live `
  --week-start YYYY-MM-DD `
  --notion-weekly-export "<actual recurring export path>"
```

Live Notion path, once the local integration is authenticated:

```powershell
$env:NOTION_API_KEY = "secret_..."
python -m tools.publish_reddit_live_notion `
  --week-start YYYY-MM-DD
```

Never commit the Notion API key.

### 5. Open Mission Control

```powershell
Start-Process .\artifacts\mission_control\latest\dashboard.html
```

Read the Captain's Console before reviewing individual artifacts.

### 6. Review the mission

Confirm:

- source health is acceptable;
- the Main and Community counts are plausible;
- no unexpected review or rejection spike exists;
- warnings are understood;
- the Main and Community posts render correctly;
- the timestamped archive exists;
- the Captain's Console recommendation matches the evidence.

### 7. Publish

Publish only from the generated Reddit artifacts after the mission has been reviewed.

Mission Control may say `HOLD FOR REVIEW` even when the renderer completed successfully. Rendering is not the same as launch approval.

## Mission Control artifacts

Stable latest copies:

```text
artifacts/mission_control/latest/dashboard.html
artifacts/mission_control/latest/flight_recorder.json
```

Timestamped archive:

```text
artifacts/mission_control/archive/<MISSION_ID>_<UTC_TIMESTAMP>/dashboard.html
artifacts/mission_control/archive/<MISSION_ID>_<UTC_TIMESTAMP>/flight_recorder.json
```

The Flight Recorder contains the project identity, Mission ID, source health, counts, knowledge totals, warnings, artifact paths, and launch decision.

## Review Console and registry maintenance

Unresolved presentation knowledge belongs in review, not in canonical output by accident.

Review kinds:

- `VENUE` → Ultimate Venues
- `HOST` → Hosts
- `ARTIST` → Artists

Notion review pushes are opt-in. Created review records must remain visibly marked with:

- `Needs Review`
- `Review Source URL`
- `Review Notes`

Existing canonical records must never be overwritten by automated review pushes.

## Degraded harvest procedure

When a required source fails:

1. Do not treat ordinary output paths as ready production artifacts.
2. Read the source reason in Mission Control.
3. Inspect the degraded artifacts under `artifacts/degraded/` when available.
4. Retry only after determining whether the failure is temporary, structural, or authentication-related.
5. Use `--allow-degraded` only as an explicit operator decision; it does not make the mission healthy.

## Unexpected review or rejection spike

1. Compare the current Flight Recorder with the previous mission archive.
2. Identify whether the change is source-specific, category-specific, geographic, or registry-related.
3. Inspect the publisher audit and review training artifacts.
4. Correct canonical knowledge in Notion where appropriate.
5. Add or update a focused regression test before changing production rules.

## Knowledge build anomalies

If corpus counts change unexpectedly:

1. Confirm the correct full-database CSV was used.
2. Confirm the export still contains the expected Notion columns.
3. Compare `generated/corpus/summary.json` with the prior build.
4. Treat Artist output as candidates unless a dedicated curated relation supports canonical identity.

## Recovery rules

- Never edit generated Reddit output as the only fix. Fix the source, registry, or deterministic presentation rule.
- Never replace an official venue, host, or artist link with a shortener.
- Strip tracking parameters while preserving the direct destination domain.
- One observed bug → one fix → focused tests → full suite → render → inspect.

## Reference Missions

Historical weeks will become frozen product-level regression missions. Each Reference Mission should eventually preserve:

- source snapshot;
- canonical events;
- Main output;
- Community output;
- review queue;
- Flight Recorder;
- Mission Control dashboard.

## End-of-mission procedure

After publishing:

1. Confirm the mission archive directory exists.
2. Record the outcome and lessons in `docs/LOGBOOK.md`.
3. Commit intentional code or documentation changes.
4. Tag major operational milestones only after the mission outcome is known.
