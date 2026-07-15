# Attempt 76 — Knowledge Drift Detection

## Goal

Detect when active venue or organizer category priors no longer match recent classified event behavior.

The detector is read-only. It never changes or retires a hint automatically.

## Inputs

- classified event history
- active venue category hints
- active organizer category hints

## Recent window

By default, the detector uses the 20 most recent classified events for each hinted entity. Older behavior remains historical context but does not hide a recent programming shift.

At least five recent events are required before drift can be assessed.

## Statuses

`STABLE`

The expected category still represents at least 80 percent of recent events.

`WATCH`

The expected category has lost between 20 and 35 percentage points of recent share. Continue monitoring.

`DRIFT`

The expected category has lost at least 35 percentage points of recent share. Review the hint before relying on it further.

`INSUFFICIENT`

Too few recent events exist to evaluate drift. Keep the current hint and gather more evidence.

## Recommendations

- `keep`
- `monitor`
- `review_hint`

Attempt 76 does not emit `retire` automatically. Retirement remains a human decision.

## Run

```powershell
python -m tools.report_knowledge_drift fixtures/real_multi_source/deduplicated_publisher_ready_events.json
```

Default artifacts:

```text
artifacts/knowledge_drift.json
artifacts/knowledge_drift_report.txt
```

A weekly fixture is a smoke test. Meaningful drift assessment requires accumulated classified history.
