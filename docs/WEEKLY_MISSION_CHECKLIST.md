# Mid-Columbia Mission Control — Weekly Mission Checklist

## Preflight

- [ ] Pull the current mission branch.
- [ ] Confirm the intended publication week.
- [ ] Confirm the recurring Notion export or live Notion integration is available.
- [ ] Run `python -m pytest -q` with no failures.

## Knowledge Core

- [ ] Rebuild the historical corpus if the full Reddit database changed.
- [ ] Review `generated/corpus/summary.json` for unexpected count changes.
- [ ] Confirm curated Notion registries remain authoritative.

## Production run

- [ ] Run `tools.publish_reddit_live` or `tools.publish_reddit_live_notion`.
- [ ] Confirm the command reports the expected Mission ID.
- [ ] Confirm Main and Community Reddit artifacts were generated.
- [ ] Confirm `artifacts/mission_control/latest/dashboard.html` exists.
- [ ] Confirm a timestamped mission archive exists.

## Captain's review

- [ ] Open the latest Mission Control dashboard.
- [ ] Review source health and warnings.
- [ ] Review harvested, deduplicated, Main, Community, review, and rejected counts.
- [ ] Investigate any unexpected review or rejection spike.
- [ ] Inspect the Main post.
- [ ] Inspect the Community post.
- [ ] Confirm Weekly Events appear only in Main and at the bottom of each day.
- [ ] Confirm venue links use Ultimate Venues presentation.
- [ ] Confirm Host and Artist credits use direct canonical links.
- [ ] Confirm no shortened or tracking-heavy destination URLs appear.

## Launch

- [ ] Captain's Console evidence is understood.
- [ ] Any `HOLD FOR REVIEW` blocker has been resolved or explicitly accepted by the operator.
- [ ] Publish the Main Reddit post.
- [ ] Publish the Community Reddit post separately.
- [ ] Record the outcome in `docs/LOGBOOK.md`.

## Closeout

- [ ] Confirm the mission archive contains `dashboard.html` and `flight_recorder.json`.
- [ ] Commit intentional mission changes.
- [ ] Push the mission branch.
- [ ] Tag an operational milestone only after a successful mission outcome.
