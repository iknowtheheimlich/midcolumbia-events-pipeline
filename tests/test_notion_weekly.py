import csv
from datetime import date
import json

from src.notion_weekly import load_notion_weekly_rows, materialize_weekly_events


def test_materializes_enabled_weekly_row_on_matching_weekday() -> None:
    events = materialize_weekly_events(
        [
            {
                "Event Name": "Trivia Night",
                "Weekly": "__YES__",
                "Generate This Week": "__YES__",
                "Days of the Week": "Wednesday",
                "Time, Price, Notes": "6:30-8:30p",
                "Venue Name": "Solar Spirits",
                "Venue URL": "https://www.solarspirits.com/",
                "City": "Richland",
            }
        ],
        week_start=date(2026, 7, 13),
    )

    assert events == [
        {
            "title": "Trivia Night",
            "start_date": "2026-07-15",
            "start_time": "18:30",
            "end_time": "20:30",
            "venue": "Solar Spirits",
            "city": "Richland",
            "url": "https://www.solarspirits.com/",
            "source": "NotionWeekly",
            "category": "Weekly Events",
            "description": "",
            "publication_target": "MAIN",
            "is_weekly": True,
            "time_price_notes": "6:30-8:30p",
        }
    ]


def test_materializes_plural_weekday_from_live_notion_values() -> None:
    events = materialize_weekly_events(
        [
            {
                "Event Name": "Monday Night Poker",
                "Weekly": True,
                "Generate This Week": True,
                "Days of the Week": "Mondays",
                "Time, Price, Notes": "6-10p",
                "Venue": "Venue",
            }
        ],
        week_start=date(2026, 7, 20),
    )

    assert [event["start_date"] for event in events] == ["2026-07-20"]


def test_materializes_each_day_for_multi_day_weekly_row() -> None:
    events = materialize_weekly_events(
        [
            {
                "Event Name": "Line Dancing Classes",
                "Weekly": True,
                "Generate This Week": True,
                "Days of the Week": "Mondays & Thursdays",
                "Venue": "Venue",
            }
        ],
        week_start=date(2026, 7, 20),
    )

    assert [event["start_date"] for event in events] == ["2026-07-20", "2026-07-23"]


def test_requires_weekly_and_generate_flags() -> None:
    rows = [
        {
            "Event Name": "Trivia Night",
            "Weekly": "__YES__",
            "Generate This Week": "__NO__",
            "Days of the Week": "Wednesday",
            "Venue Name": "Solar Spirits",
        },
        {
            "Event Name": "Open Mic",
            "Weekly": "__NO__",
            "Generate This Week": "__YES__",
            "Days of the Week": "Thursday",
            "Venue Name": "Venue",
        },
    ]

    assert materialize_weekly_events(rows, week_start=date(2026, 7, 13)) == []


def test_skips_rows_without_usable_date_or_weekday() -> None:
    rows = [
        {
            "Event Name": "Mystery Recurrence",
            "Weekly": "__YES__",
            "Generate This Week": "__YES__",
            "Venue Name": "Venue",
        }
    ]

    assert materialize_weekly_events(rows, week_start=date(2026, 7, 13)) == []


def test_explicit_date_must_fall_inside_window() -> None:
    rows = [
        {
            "Event Name": "Friday Event",
            "Weekly": True,
            "Generate This Week": True,
            "Date": "2026-07-17",
            "Venue": "Venue",
        },
        {
            "Event Name": "Next Week Event",
            "Weekly": True,
            "Generate This Week": True,
            "Date": "2026-07-20",
            "Venue": "Venue",
        },
    ]

    events = materialize_weekly_events(rows, week_start=date(2026, 7, 13))

    assert [event["title"] for event in events] == ["Friday Event"]


def test_deduplicates_same_event_venue_date_and_time() -> None:
    row = {
        "Event Name": "Trivia Night",
        "Weekly": True,
        "Generate This Week": True,
        "Days of the Week": "Wednesday",
        "Time, Price, Notes": "7p",
        "Venue": "Venue",
    }

    events = materialize_weekly_events([row, dict(row)], week_start=date(2026, 7, 13))

    assert len(events) == 1


def test_uses_notion_venue_reddit_combo_as_authoritative_presentation() -> None:
    events = materialize_weekly_events(
        [
            {
                "Event Name": "Open Mic",
                "Weekly": True,
                "Generate This Week": True,
                "Days of the Week": "Thursday",
                "Time, Price, Notes": "7p",
                "Venue Reddit Combo": "[The Emerald of Siam](https://www.emeraldofsiam.com/), Richland",
            }
        ],
        week_start=date(2026, 7, 13),
    )

    assert events[0]["venue"] == "The Emerald of Siam"
    assert events[0]["city"] == "Richland"
    assert events[0]["url"] == "https://www.emeraldofsiam.com/"
    assert events[0]["venue_reddit_combo"] == (
        "[The Emerald of Siam](https://www.emeraldofsiam.com/), Richland"
    )


def test_loads_csv_export(tmp_path) -> None:
    path = tmp_path / "weekly.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Event Name", "Weekly"])
        writer.writeheader()
        writer.writerow({"Event Name": "Trivia Night", "Weekly": "Yes"})

    assert load_notion_weekly_rows(path) == [
        {"Event Name": "Trivia Night", "Weekly": "Yes"}
    ]


def test_loads_json_results_export(tmp_path) -> None:
    path = tmp_path / "weekly.json"
    path.write_text(
        json.dumps({"results": [{"Event Name": "Trivia Night", "Weekly": True}]}),
        encoding="utf-8",
    )

    assert load_notion_weekly_rows(path) == [
        {"Event Name": "Trivia Night", "Weekly": True}
    ]
