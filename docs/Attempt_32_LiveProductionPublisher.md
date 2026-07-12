# Attempt_32_LiveProductionPublisher

The production Reddit command now harvests registered live sources, loads the generated Venue Registry, runs venue resolution, geographic intelligence, content screening, recurrence splitting, deduplication, publisher projection, editorial policy, weekly filtering, and Reddit rendering in one process.

Run:

```powershell
python -m tools.publish_reddit_live --week-start 2026-07-12
```

Generated output remains under `artifacts/reddit/`. Tracked fixtures are not used as production event input and are never rewritten by this command.

The command prints harvest warnings rather than silently hiding source failures. Events classified for review or rejection are counted but excluded from the Reddit artifact.
