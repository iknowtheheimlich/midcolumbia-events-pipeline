from datetime import date

from src.notion_weekly import materialize_weekly_events


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
            "start_time": "06:30",
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
