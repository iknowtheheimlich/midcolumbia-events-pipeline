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

Pipeline-owned, Captain-owned, and derived properties are declared separately in `src/notion_weekly_curation.py`. Normal synchronization sends no Captain-owned properties, so Notion values survive every upsert. Duplicate keys, malformed Captain selects, and incomplete read-back are hard failures. Missing rows are retained; synchronization never deletes pages.

The database currently has an All Events/default table. `Needs Review`, `Included`, and `Excluded` are operator views; creating them is optional and never changes row data.

Curated render fails closed when Notion is unavailable, the inventory/audit boundary is absent or changed, keys are duplicated, Captain selects are malformed, or Notion rows do not exactly reconcile with the frozen pipeline inventory. There is no autonomous fallback. `--excel-fallback` is deliberately rejected until a separately reviewed explicit fallback workflow exists.

Prepare mode freezes source-health evidence in the sync audit. Curated render cannot report readiness without that evidence or unless Mission Control returns `READY TO PUBLISH`.
