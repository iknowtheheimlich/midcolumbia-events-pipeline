# Notion Final Post Ready Two-Export Assembly SOP

## Scope

This SOP applies only to:

```powershell
python -m tools.build_reddit_post_from_exports <dated.csv> <recurring.csv> <output.txt> --week-start YYYY-MM-DD
```

It documents the focused assembly path implemented by
`tools.build_reddit_post_from_exports`. It is not the canonical live production
command.

## Inputs

Provide two CSV files:

1. A dated export for one-time and multi-day events, with these expected
   columns:
   - `Date`
   - `Category`
   - `Event Name`
   - `Final Post Ready`
2. A recurring export for weekly templates, with these expected columns:
   - `Day` or `Weekday`
   - `Category`
   - `Event Name`
   - `Final Post Ready`

The dated export may also use `Multi Days`, `Multi-Day`, `Multi Day`, or
`Event Type` to identify multi-day rows.

`--week-start` is required and must identify a Monday. Use an ISO date such as
`2026-07-27`.

## Assembly behavior

The assembler:

- generates a Monday-through-Sunday document for the requested week;
- creates `Events`, `Multi-Day Events`, and `Happening Every <Weekday>`
  sections for each day;
- groups rows by category using the deterministic category order defined by
  the tool;
- preserves input order among rows within the same category;
- emits each non-empty `Final Post Ready` value verbatim without reconstructing
  or editorially rewriting it;
- omits rows whose `Final Post Ready` value is empty; and
- writes the selected output path as UTF-8 plain text.

The generated layout intentionally leaves blank lines between event listings.
Preserve that spacing: it gives the operator usable separation when reviewing
and editing the post from a phone.

## Failure behavior

The command fails rather than inventing data when:

- an input file is missing or unreadable;
- a CSV has no header;
- a dated row contains an unsupported date value;
- a recurring row contains an unsupported weekday value; or
- `--week-start` is not a Monday.

Rows without a usable date or weekday are not placed. Rows without a non-empty
`Final Post Ready` value are omitted. The operator must treat unexpected
omissions as an input-review issue rather than reconstructing event text in the
generated output.

## Operator review

The following checks are manual operator review steps. The assembler does not
claim to automate or guarantee them:

- Confirm the correct dated export, recurring export, and publication week were
  selected.
- Confirm the expected input columns are present before running the command.
- Confirm the output covers Monday through Sunday and uses the expected section
  and category order.
- Compare emitted listings with the source `Final Post Ready` values and confirm
  they remain verbatim.
- Confirm rows with empty `Final Post Ready` values were intentionally omitted.
- Inspect for duplicate events, duplicate URLs, missing venue, time, or category
  information, malformed Markdown, and blank event text.
- Confirm links are direct destination links rather than shortened URLs.
- Preserve the intentional blank-line spacing during final mobile review.

Report input or output defects. Do not silently repair generated text as a
substitute for correcting the source export.

## Authority boundary

This focused path does not perform:

- live source harvesting;
- canonical event reconciliation or knowledge updates;
- Main/Community dual-publication routing;
- Mission Control recording or launch approval; or
- automated operator QC.

Successful assembly means only that the requested text artifact was generated.
It does not make a weekly production mission complete or authorize publication.
Use the repository's current `AGENTS.md`, Mission Operations Manual, and weekly
checklist for repository-wide governance and live production procedure.
