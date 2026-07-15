# Attempt 81 — Classification Review Feedback

## Goal

Capture human category reviews as durable evidence and summarize recurring classifier errors without automatically changing rules, hints, or precedence.

## Ledger

Reviews are appended to:

```text
history/classification_reviews.jsonl
```

Each record preserves the original category, corrected category, confidence, reason, structured evidence, source, venue, organizer, reviewer, and timestamp.

## Record a review

For a single-event JSON file:

```powershell
python -m tools.record_classification_review event.json "Classes/Workshops"
```

For a multi-event JSON artifact:

```powershell
python -m tools.record_classification_review events.json "Classes/Workshops" --event-id <event-id>
```

Recording the same review twice is idempotent.

## Analyze reviews

```powershell
python -m tools.report_classification_reviews
```

Outputs:

```text
artifacts/classification_review_summary.json
artifacts/classification_review_report.txt
```

The report includes override rate, category transitions, implicated decision reasons, sources, venues, organizers, and confidence bands.

## Guardrail

Attempt 81 is observational. It does not promote title rules, edit venue or organizer hints, or alter classifier precedence. Evidence must accumulate before a later governed attempt proposes rule changes.
