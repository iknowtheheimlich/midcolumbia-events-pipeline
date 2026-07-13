# Attempt_53_HarvestHealthGate

## Objective

Prevent incomplete fallback harvests from overwriting normal production artifacts or entering the review-learning corpus.

## Source states

- `LIVE`: required active source completed a clean live fetch.
- `PARTIAL`: live fetch failed but a normalized fixture supplied fallback events.
- `CACHED`: normalized data was deliberately reused without a live fetch.
- `FAILED`: no usable events remain.
- `OPTIONAL`: non-active sources such as migration bridges do not determine production health.

## Gate

Normal production requires every selected active source to be `LIVE`.

When coverage is degraded and `--allow-degraded` is absent:

- normal Reddit, audit, and metrics artifacts are not overwritten;
- inspection artifacts are written under `artifacts/degraded/`;
- review training is skipped;
- the command exits with status 2.

`--allow-degraded` explicitly permits normal artifact paths and review training while retaining a degraded status report.

## Rationale

Fixture fallback is operationally useful for diagnosis, but it must not masquerade as a complete weekly harvest. Plausible incomplete output is more dangerous than a visible failure.
