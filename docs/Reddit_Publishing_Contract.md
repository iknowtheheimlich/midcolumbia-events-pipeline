# Reddit Weekly Publishing Contract

The weekly Reddit artifact is assembled from two independent Notion CSV exports.

## Inputs

1. **Reddit publishing view**
   - Required columns: `Date`, `Category`, `Event Name`, `Final Post Ready`
   - Contains one-time events and date-range events.
   - Must not contain recurring-template rows.

2. **Recurring Templates Library**
   - Required columns: `Days of the Week`, `Category`, `Event Name`, `Final Post Ready`
   - Contains events that happen every named weekday.
   - Recurring templates do not need a value in the `Date` property.
   - Ordinal schedules such as `2nd Thursday` are not weekly templates. Add their
     actual dated occurrence to the weekly publishing view.

`Final Post Ready` is copied verbatim. The publisher does not reconstruct links,
venue text, host text, times, prices, or notes.

## Daily output

Each Monday-through-Sunday block may contain:

```text
# Monday, July 27

## Events

(category blocks for one-time dated events)

## Multi-Day Events

(category blocks for date ranges active that day)

## Happening Every Monday

(category blocks from the recurring template export)
```

Empty sections and empty categories are omitted.

There is exactly one blank line between every logical block: day heading,
section heading, category heading, event listing, next event, next category,
and next section.

## Category order

1. Events/Hangouts
2. Classes/Workshops
3. Music/Comedy
4. Sports
5. Restaurants/Bars/Wineries
6. Art/Theater
7. Trivia/Game Night
8. Karaoke/Open Mic
9. Fundraisers
10. Markets
11. Community Programs
12. School District Event
13. Tours
14. Festivals/Fair
15. Estate/Yard/Garage Sales
16. Faith Based

Unknown categories fail the run rather than being silently reordered or dropped.

## Command

```powershell
python -m tools.build_reddit_post `
  "path\to\Reddit Publishing.csv" `
  "path\to\Recurring Templates Library.csv" `
  --week-start 2026-07-27
```

The default artifact is:

```text
artifacts/Weekly_Reddit_Post_2026-07-27.txt
```

Use `--output` to choose another path.

The command stops with a clear error when the wrong Notion view was exported,
a required value is blank, the week start is not Monday, a date is invalid, or
a recurring schedule is not an every-week weekday rule.
