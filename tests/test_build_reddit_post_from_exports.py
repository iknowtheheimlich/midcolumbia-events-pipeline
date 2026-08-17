from datetime import date

import pytest

from tools.build_reddit_post_from_exports import build_reddit_post


def test_builds_dated_multi_day_and_recurring_sections_from_separate_sources() -> None:
    dated = [
        {
            "Date": "2026-07-27",
            "Category": "Music/Comedy",
            "Event Name": "Concert",
            "Final Post Ready": "Concert markdown",
            "Multi Days": "",
        },
        {
            "Date": "2026-07-27",
            "Category": "Art/Theater",
            "Event Name": "Exhibit",
            "Final Post Ready": "Exhibit markdown",
            "Multi Days": "yes",
        },
    ]
    recurring = [
        {
            "Day": "Monday",
            "Category": "Trivia/Game Night",
            "Event Name": "Weekly Trivia",
            "Final Post Ready": "Trivia markdown",
        }
    ]

    result = build_reddit_post(dated, recurring, date(2026, 7, 27))

    monday = result.split("# Tuesday, July 28", 1)[0]
    assert monday == (
        "# Monday, July 27\n"
        "\n"
        "## Events\n"
        "\n"
        "**Music/Comedy**\n"
        "Concert markdown\n"
        "\n"
        "## Multi-Day Events\n"
        "\n"
        "**Art/Theater**\n"
        "Exhibit markdown\n"
        "\n"
        "## Happening Every Monday\n"
        "\n"
        "**Trivia/Game Night**\n"
        "Trivia markdown\n"
        "\n"
    )


def test_final_post_ready_is_preserved_verbatim() -> None:
    markdown = "**Event** | [Venue](https://example.com), Kennewick | 7:00 PM"
    result = build_reddit_post(
        [
            {
                "Date": "2026-07-27",
                "Category": "Events/Hangouts",
                "Final Post Ready": markdown,
            }
        ],
        [],
        date(2026, 7, 27),
    )

    assert markdown in result


def test_recurring_rows_do_not_require_or_use_a_date() -> None:
    result = build_reddit_post(
        [],
        [
            {
                "Weekday": "Mon",
                "Category": "Markets",
                "Final Post Ready": "Recurring market markdown",
            }
        ],
        date(2026, 7, 27),
    )

    assert "Recurring market markdown" in result.split("## Happening Every Monday", 1)[1]
    assert "Recurring market markdown" not in result.split("## Events", 1)[1].split(
        "## Multi-Day Events", 1
    )[0]


def test_rejects_non_monday_week_start() -> None:
    with pytest.raises(ValueError, match="Monday"):
        build_reddit_post([], [], date(2026, 7, 28))
