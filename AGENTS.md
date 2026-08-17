# AGENTS.md

Operating manual for autonomous software agents working in this repository.

## 1. Project Purpose

Mid-Columbia Mission Control is a local-first event intelligence and publishing
system for public events in the Mid-Columbia region. It turns scattered source
listings into normalized, deduplicated, explainable, reviewable event knowledge
and publisher-ready artifacts.

The operating flow is:

`Discover -> Curate -> Verify -> Publish`

Reddit is the first production publisher, not the system of record or the limit
of the architecture. Canonical knowledge, provenance, review state, and mission
telemetry must remain usable by other publishers.

Authoritative project documents:

- `docs/PROJECT_CHARTER.md`
- `docs/VISION.md`
- `docs/Architecture.md`
- `docs/Mission_Operations_Manual.md`
- `docs/WEEKLY_MISSION_CHECKLIST.md`
- `docs/RELEASE_CHECKLIST.md`
- `README.md`

Historical `docs/Attempt_*` and `docs/attempts/` files explain how features were
built. They are implementation records, not the current operating contract when
they conflict with the files above or with tested behavior.

## 2. Primary Mission

The primary mission is to produce the weekly Mid-Columbia Reddit event
publication reliably, predictably, and with as little manual repair as possible.

Every production change must do at least one of the following:

- reduce the operator's time required for the next weekly publication;
- improve the accuracy or completeness of the published list;
- make uncertainty, source failure, or launch risk visible before publication;
- preserve a correction so it improves later missions;
- protect an existing publishing or data contract.

Prefer the smallest change that advances the weekly mission. A technically
interesting feature that does not help the next publication belongs on the
backlog.

## 3. Current Pipeline Architecture

The high-level production path is:

```text
Public sources / Notion weekly input
    -> source harvesters and adapters
    -> canonical normalization
    -> venue, geography, category, time, and content intelligence
    -> recurrence separation
    -> conservative deduplication and occurrence resolution
    -> publisher and editorial projections
    -> Main / Community routing and program grouping
    -> Reddit renderer and audit artifacts
    -> Mission Control launch decision and archive
```

Architectural boundaries are contracts:

1. Source-specific acquisition and parsing stay in `adapters/`.
2. Adapters emit the shared event schema; publishers do not parse source HTML.
3. Canonical and curated knowledge outranks harvested presentation data.
4. Deduplication is conservative and preserves source attribution.
5. Unknown or low-confidence data is routed to review rather than guessed.
6. Analysis and reports do not silently mutate canonical decisions.
7. Rendering success is not launch approval. Mission Control may still return
   `HOLD FOR REVIEW`.
8. Generated runtime artifacts do not automatically become golden fixtures or
   canonical knowledge. Promotion into a Reference Mission requires explicit
   review and authorization.
9. Notion is an editorial input/consumer, not a required core runtime.

## 4. Major Components

### Harvest and adapters

- `adapters/registry.py` and `config/source_registry.json` define source
  enablement, priority, attribution, fixture paths, and status.
- `adapters/harvest.py` coordinates raw acquisition and adapter normalization.
- Source packages under `adapters/` isolate source-specific behavior.
- Enabled sources currently include Visit Tri-Cities, Tri-City Vibe, Richland
  Library, Mid-Columbia Libraries, AllEvents, and the legacy CSV migration
  bridge.

### Canonical pipeline and intelligence

- `src/pipeline.py` is the source-agnostic pipeline spine and owns the output
  queues.
- `src/text_normalization.py`, `src/time_semantics.py`, `src/geography.py`,
  `src/category_intelligence.py`, and related intelligence modules enrich
  normalized events.
- `src/venue_registry.py` resolves curated venue identity and presentation.
- `src/deduplicate.py` and `src/occurrence_resolution.py` handle conservative
  duplicate and cross-source occurrence resolution.
- `src/recurrence_classifier.py` keeps publisher-ready occurrences separate from
  recurrence review.

### Editorial and publishing

- `src/publisher_projection.py` creates publisher-facing records.
- `src/publisher_editorial.py` applies deterministic display, disposition, and
  Main/Community routing policy.
- `src/program_intelligence.py` groups related occurrences for display.
- `src/publishing_contract.py` and
  `config/reddit_publishing_profile.json` own category vocabulary, ordering,
  routing, and compact time grammar.
- `src/reddit_renderer.py` renders canonical Reddit Markdown artifacts.

### Production commands

- `tools/publish_reddit_live.py` is the canonical live production command. It
  harvests sources, runs the full pipeline, writes dual Reddit artifacts and
  audits, and records Mission Control.
- `tools/publish_reddit_live_notion.py` wraps the live command with authenticated
  Notion weekly rows.
- `tools/build_reddit_post_from_exports.py` is the focused two-export assembly
  path. It combines dated and recurring CSV exports into a Monday-through-Sunday
  post while preserving `Final Post Ready` verbatim.
- `tools/finalize_weekly_run.py` updates durable review/corpus operations and
  weekly health artifacts for an existing event set.

### Review, history, and operations

- Review modules under `src/review_*` and classification-review tools preserve
  human decisions and expose backlog, SLA, throughput, and capacity.
- `history/` contains durable classified and review state. Treat it as
  operational data, not disposable output.
- `src/mission_control.py`, mission summary/archive modules, and
  `src/operational_dashboard.py` produce launch status, Flight Recorder records,
  stable latest artifacts, and immutable mission archives.

## 5. Repository Layout

```text
adapters/       Source manifests, harvesters, requests, and parsers
config/         Versioned source, editorial, publishing, and intelligence policy
docs/           Current contracts plus historical implementation records
fixtures/       Stable raw/normalized regression inputs and expected data
history/        Durable review and classified-event state
src/            Source-agnostic pipeline, intelligence, publishing, and ops logic
tests/          Contract, regression, fixture, and operational tests
tools/          Operator-facing CLI modules
artifacts/      Generated reports and publisher outputs; some samples are tracked
generated/      Local generated knowledge/registry output; gitignored
```

Root entry points and manifests include `README.md`, `requirements.txt`,
`requirements-dev.txt`, `run_tests.bat`, and `run_publish_reddit_live.bat`.

Do not write runtime output into `fixtures/`. Do not commit `.env`, credentials,
Notion API keys, local absolute paths, generated Mission Control runs, or
unrelated runtime artifacts.

## 6. Engineering Philosophy

- Start from the weekly operator problem, then choose the smallest coherent
  change.
- Inspect code, tests, current contracts, and recent history before changing
  behavior. Do not infer architecture from filenames alone.
- Prefer deterministic rules and explicit precedence over fuzzy guesses.
- Preserve provenance and reasons with inferred values.
- Keep canonical knowledge human-curated. Harvesters propose facts; they do not
  silently redefine truth.
- Quarantine uncertainty. A review queue is better than a confident bad event.
- Fix the source, registry, or deterministic rule. Do not manually edit generated
  Reddit output as the only fix.
- One observed bug -> one focused fix -> focused regression test -> full suite ->
  rendered artifact inspection when publishing changes.
- Keep schema changes backward-compatible where practical. Existing fields do
  not change type, meaning, or required behavior without an explicit migration.
- Protect golden fixtures. Live runs must not overwrite them.
- Avoid parallel systems that duplicate the event schema, venue registry,
  resolver, category vocabulary, or publisher rules.
- Do not refactor adjacent code merely because it is available. Repository
  archaeology is not a weekly deliverable.

When documentation and implementation disagree, tests and current production
behavior establish the immediate truth. Correct the stale documentation in the
same change when it is in scope.

## 7. Git Workflow

1. Inspect `git status --short --branch`, the current branch, its upstream, and
   recent history before editing.
2. Use the production line identified by the operator and verified from current
   repository/remote state. Do not assume the default branch contains the
   current production system.
3. Fetch when authorized and available. Pull only in a clean worktree, on the
   intended branch, when updating that branch is authorized.
4. Create a narrowly named branch for autonomous work unless the operator
   explicitly directs work on the current branch.
5. Preserve all pre-existing user changes. Never discard, rewrite, stage, or
   commit unrelated work.
6. Stage explicit paths. Review `git diff --check`, the staged diff, and staged
   file names before committing.
7. Use a terse imperative commit subject describing the completed change.
8. Do not push, force-push, rebase shared work, create a PR, merge, tag, or
   publish artifacts unless the operator explicitly requests that action.
9. A PR-ready commit means a scoped commit with a clean relevant diff and
   recorded validation; it does not imply permission to push.

## 8. Testing Expectations

The full regression gate from the repository root is:

```bash
python -m pytest -q
```

On Windows, `run_tests.bat` is the convenience wrapper. Install development
dependencies from `requirements-dev.txt`; Playwright Chromium is required for a
clean environment.

Rules:

- Run focused tests while developing and the full suite before completion.
- New behavior requires a focused contract or regression test.
- A refactor must prove that observable behavior did not change.
- The exact test count may increase. It must not decrease without an explained
  test-suite audit.
- No failures, collection errors, unexpected skips, or unexplained warnings are
  acceptable.
- Documentation-only changes still require the full suite because the repository
  release contract requires a green baseline.
- If dependencies or external services prevent a test, report the exact command,
  boundary, and unverified scope. Do not call the change complete.

For production-path changes, also run the smallest relevant command or
fixture-backed smoke test and inspect the resulting Markdown or dashboard.
Live harvesting is not a substitute for deterministic fixture-backed tests.

## 9. Reddit Publishing Contract

The canonical live publisher writes:

```text
artifacts/reddit/Main_Events_Post.txt
artifacts/reddit/Community_Events_Post.txt
```

The governing profile is `config/reddit_publishing_profile.json`.

Required behavior:

- Publish only records with `AUTO_PUBLISH` disposition.
- Route categories according to the publishing profile. Missing/unknown
  categories go to review; they are not silently assigned.
- Keep Main and Community output separate.
- Group output by date, then by profile category order.
- Sort events chronologically; use title and venue only as deterministic
  tie-breakers.
- Use date headings in `#DD Month` form for canonical rendered artifacts.
- Render event lines as:
  `Event | [Canonical Venue](direct URL), City | compact time`
- Add canonical Host and Artist credits with direct links when available.
- Use compact time grammar such as `9a`, `10:30a`, `1p`, and `5-6p`.
- Preserve a blank line between event listings.
- Preserve unexpected but valid categories after configured categories rather
  than dropping their events.
- Preserve source attribution through deduplication and render a truthful,
  dynamically derived attribution footnote for live runs.
- Keep recurrence review, editorial review, publication blockers, rejected
  events, and content-rejected events out of publishable output.
- `Weekly Events` belong in Main. The weekly operator checklist additionally
  requires them at the bottom of each day.
- Use canonical venue presentation and direct destination URLs. Strip tracking
  parameters; do not substitute shortened links.

The two-export assembler has a separate, deliberately narrow contract:

- dated CSV rows supply one-time and multi-day events;
- recurring CSV rows supply weekday templates and do not require dates;
- `week_start` must be a Monday;
- each day renders `Events`, `Multi-Day Events`, then
  `Happening Every <Weekday>`;
- `Final Post Ready` is emitted verbatim and must not be reconstructed;
- rows without `Final Post Ready` are omitted.

Do not casually merge these contracts. Change either only with corresponding
tests and an explicit operator-facing reason.

## 10. Current Priorities

Prefer work that reduces weekly operator effort or prevents an observed
production fault; do not expand scope without mission authority.

## 11. Out-of-Scope Work

Unless explicitly requested, do not:

- invent new architecture, orchestration layers, registries, or schemas;
- add speculative sources, publishers, dashboards, AI classifiers, or
  integrations;
- redesign Notion or make it a hard dependency of the core pipeline;
- auto-promote uncertain venues, hosts, artists, or inferred entities;
- perform broad cleanup, renaming, typing, formatting, or dependency upgrades;
- rewrite historical attempt documents;
- replace deterministic policy with opaque inference;
- edit generated output as the permanent fix;
- change category taxonomy or Reddit presentation for aesthetic preference;
- expand work solely toward future maps, calendars, APIs, Home Assistant,
  Discord, or analytics outputs;
- run destructive git operations or mutate durable history without explicit
  operator authorization and a recovery plan.

## 12. Definition of Done

A task is done only when all applicable conditions are true:

- The change solves the stated operator problem without unrelated expansion.
- Current architecture and contracts were verified in code and tests.
- Source-specific logic remains in adapters and publisher logic remains
  source-agnostic.
- New or changed behavior has focused tests.
- `python -m pytest -q` passes in full with no unexplained reduction in test
  count.
- Relevant production or rendering smoke tests pass and outputs were inspected.
- Generated files, fixtures, durable history, credentials, and local paths were
  not accidentally changed or staged.
- Documentation was updated when workflow, behavior, schema, or operational
  expectations changed.
- `git diff --check` passes.
- The staged diff contains only intended files.
- The commit is scoped, understandable, and ready for review.
- The final handoff states the branch, commit SHA, validation command and result,
  and any remaining operational risk or unverified boundary.

For a weekly production mission, Done additionally requires reviewed Main and
Community artifacts, an understood Captain's Console decision, and a valid
timestamped Mission Control archive. `HOLD FOR REVIEW` is not Done unless the
operator explicitly accepts and resolves the blocker.
