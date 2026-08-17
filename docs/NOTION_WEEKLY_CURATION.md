# Weekly Curation control surface

`Weekly Curation` is the explicit human boundary between acquisition and curated rendering. Neither mode publishes.

Prepare a week (harvests, runs the current pipeline, synchronizes, writes the frozen inventory and audit, then stops):

```powershell
$env:NOTION_TOKEN='<integration token>'
python -m tools.publish_reddit_live --week-start 2026-08-10 --prepare-curation
```

After Captain review, render that exact inventory without harvesting. The command runs the existing publisher audit and the same Mission Control gate/archive sequence as live production, then stops before publication:

```powershell
$env:NOTION_TOKEN='<integration token>'
python -m tools.render_reddit_curated --week-start 2026-08-10
```

Database: <https://app.notion.com/p/971914760da0416f970beea53a2b49a0>

Data source: `c4d70d49-4009-4607-a003-9ccb2c302634`

Identity is `SHA-256(v1 | publication week | case-folded source | source event ID | occurrence date)`. When the source ID is absent, the stable fallback replaces it with case-folded original title, original venue, and original time. Row number, ordering, Captain fields, category, target, and disposition never participate.

Supported multi-day source ranges are expanded into one occurrence per in-week calendar date before dispositions, deduplication, occurrence resolution, curation, and rendering. Each row carries `Event Date` for the occurrence plus pipeline-owned `Source Start Date`, `Source End Date`, `Occurrence Identity`, and `Source Time Evidence`. These properties preserve the original range and structured time evidence without copying Captain decisions between sibling dates. The live data-source schema must contain these four pipeline-owned properties before the first prepare run using this version.

Pipeline-owned, Captain-owned, and derived properties are declared separately in `src/notion_weekly_curation.py`. Normal synchronization sends no Captain-owned properties, so Notion values survive every upsert. Duplicate keys, malformed Captain selects, and incomplete read-back are hard failures. Missing rows are retained; synchronization never deletes pages.

Post-curation validation reconciles the exact frozen Curation Key cohort and separately verifies the retained keys recorded by PREPARE. A Captain Category derives its default Main/Community target from the publishing profile unless Captain Target explicitly overrides it. Captains Venue Override resolves the single related Ultimate Venues page and applies its canonical name and direct URL while retaining frozen city or URL evidence when the venue record does not provide an explicit replacement. Captain Description Override replaces only the editorial projection description; frozen pipeline evidence remains unchanged.

The database currently has an All Events/default table. `Needs Review`, `Included`, and `Excluded` are operator views; creating them is optional and never changes row data.

Curated render fails closed when Notion is unavailable, the inventory/audit boundary is absent or changed, keys are duplicated, Captain selects are malformed, or Notion rows do not exactly reconcile with the frozen pipeline inventory. There is no autonomous fallback. `--excel-fallback` is deliberately rejected until a separately reviewed explicit fallback workflow exists.

Prepare mode freezes source-health evidence in the sync audit. Curated render cannot report readiness without that evidence or unless Mission Control returns `READY TO PUBLISH`.
