# Live Notion Weekly Events Setup

The production wrapper reads curated recurring events from the Reddit Operations workspace and passes them through the normal publisher pipeline.

## Notion structure

Canonical IDs are stored in `config/notion_sources.json`:

- Reddit Operations parent page
- Reddit recurring-events data source
- Ultimate Venues data source
- Hosts data source

## One-time setup

1. Create a read-only internal Notion integration.
2. Share the `Reddit Operations` page with that integration. Confirm the integration can access the Reddit, Ultimate Venues, and Host databases below it.
3. Store the integration secret locally. Never commit it.

For the current PowerShell window:

```powershell
$env:NOTION_API_KEY = "secret_..."
```

## Publish

```powershell
python -m tools.publish_reddit_live_notion `
  --week-start 2026-07-13
```

The live wrapper queries only records where both `Weekly` and `Generate This Week` are checked, follows the `🌆 Ultimate Venues` relation, writes a temporary JSON export, invokes the stable production publisher, and removes the temporary file.

The existing `--notion-weekly-export` CSV/JSON path remains available as an offline fallback.
