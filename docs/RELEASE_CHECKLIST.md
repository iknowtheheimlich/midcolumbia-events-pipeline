# v1.0 Release Checklist

This checklist is the release gate for `v1.0.0`. A release is blocked until every required item is verified on the release branch.

## 1. Repository State

- [ ] Working tree is clean except intentionally ignored local artifacts.
- [ ] Release branch is current with `attempt-72-category-completion-pass-1`.
- [ ] No untracked HAR files, generated artifacts, secrets, credentials, or local machine paths are staged.
- [ ] README describes the current pipeline.
- [ ] CHANGELOG contains a v1 release entry.

## 2. Regression Gate

Run from the repository root:

```powershell
python -m pytest
```

Required baseline:

```text
430 passed
```

- [ ] Full suite passes with no failures or collection errors.
- [ ] No tests are skipped unexpectedly.
- [ ] No warnings indicate deprecated or unstable runtime behavior.

The exact test count may increase, but it may not decrease without an explained test-suite audit.

## 3. Weekly Operational Smoke Test

Run:

```powershell
python -m tools.finalize_weekly_run fixtures/real_multi_source/deduplicated_publisher_ready_events.json
```

Verify:

- [ ] Classified history updates successfully.
- [ ] A corpus snapshot is created when prior history exists.
- [ ] Review backlog state is written.
- [ ] Throughput history is appended exactly once.
- [ ] Review batch CSV is generated.
- [ ] Effective review configuration is persisted.
- [ ] Consolidated review metrics are persisted.
- [ ] Plaintext and JSON weekly dashboards are generated.
- [ ] Any non-blocking report failures are investigated before release.

## 4. Dashboard Gate

Inspect:

```text
artifacts/weekly_pipeline_health.txt
artifacts/weekly_pipeline_health.json
```

- [ ] Dashboard status is understood and supported by the underlying artifacts.
- [ ] `DEGRADED` blocks release until the cause is resolved.
- [ ] `ATTENTION` requires explicit operator review and documented acceptance.
- [ ] `HEALTHY` does not replace inspection of publisher-ready output.

## 5. Publishing Contract

- [ ] Publisher-ready event count is plausible for the fixture/run period.
- [ ] Recurrence and review queues remain separate from publisher-ready output.
- [ ] Source attribution survives deduplication.
- [ ] Reddit rendering preserves chronological ordering and editorial formatting.
- [ ] No venue or organizer prior overrides stronger category evidence.

## 6. Durable State Safety

Before a production weekly run:

- [ ] Back up `history/classified_events.jsonl`.
- [ ] Back up `history/classification_reviews.jsonl`.
- [ ] Back up `history/review_backlog.json`.
- [ ] Back up `history/review_backlog_throughput.jsonl`.
- [ ] Confirm the newest snapshot can be read and compared with the live corpus.

## 7. Configuration Verification

Inspect:

```text
artifacts/review_operations_config.json
```

- [ ] Stale threshold is intentional.
- [ ] Due-soon threshold is intentional.
- [ ] Overdue age exceeds due-soon age.
- [ ] Overdue appearance threshold is intentional.
- [ ] Capacity lookback is intentional.
- [ ] No command-line override was supplied accidentally.

## 8. Dependency and Clean-Checkout Gate

The final release must reproduce outside the long-lived development environment.

- [ ] Python version recorded.
- [ ] `requirements.txt` exists and installs successfully.
- [ ] `requirements-dev.txt` exists and installs successfully.
- [ ] Runtime and development dependencies are separated.
- [ ] Transitive dependencies are not pinned directly without a reason.
- [ ] Playwright Chromium is installed after package installation.
- [ ] Full suite passes in a new virtual environment.
- [ ] Canonical weekly smoke test passes in that environment.

Clean-environment validation:

```powershell
python -m venv .venv-release
.\.venv-release\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest
python -m tools.finalize_weekly_run fixtures/real_multi_source/deduplicated_publisher_ready_events.json
```

After validation:

```powershell
deactivate
Remove-Item -Recurse -Force .venv-release
```

## 9. Final v1.0.0 Gate

- [ ] Release candidate completed at least one real weekly cycle.
- [ ] No unexplained corpus drift occurred.
- [ ] Review ledger import remained idempotent.
- [ ] Backlog and throughput histories remained internally consistent.
- [ ] Dependency manifests are committed.
- [ ] Installation and canonical run instructions were verified from a clean checkout or isolated virtual environment.
- [ ] `v1.0.0` release notes are final.
- [ ] Final tag points to the exact verified commit.
