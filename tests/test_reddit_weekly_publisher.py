from datetime import date
from pathlib import Path

import pytest

from src.reddit_weekly_publisher import (
    RedditPublishingError,
    build_weekly_reddit_post,
    load_recurring_export,
    load_weekly_export,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_builds_independent_daily_multi_day_and_recurring_sections(tmp_path: Path) -> None:
    weekly = _write(
        tmp_path / "weekly.csv",
        """Date,Category,Event Name,Final Post Ready
07/27/2026,Events/Hangouts,One Night,One Night | [Venue](https://example.com) | 8p
07/27/2026 → 07/29/2026,Classes/Workshops,Camp,Camp | [Venue](https://example.com) | 9a
""",
    )
    recurring = _write(
        tmp_path / "recurring.csv",
        """Days of the Week,Category,Event Name,Final Post Ready
Mondays,Faith Based,Weekly Group,Weekly Group | [Host](https://example.com) | 6p
Tuesdays,Trivia/Game Night,Trivia,Trivia | [Venue](https://example.com) | 7p
""",
    )

    output = build_weekly_reddit_post(
        load_weekly_export(weekly),
        load_recurring_export(recurring),
        week_start=date(2026, 7, 27),
    )

    monday = output.split("# Tuesday, July 28", 1)[0]
    assert "## Events\n\n**Events/Hangouts**\n\nOne Night" in monday
    assert "## Multi-Day Events\n\n**Classes/Workshops**\n\nCamp" in monday
    assert "## Happening Every Monday\n\n**Faith Based**\n\nWeekly Group" in monday
    assert "Trivia |" not in monday

    tuesday = output.split("# Tuesday, July 28", 1)[1].split(
        "# Wednesday, July 29", 1
    )[0]
    assert "One Night |" not in tuesday
    assert "## Multi-Day Events\n\n**Classes/Workshops**\n\nCamp" in tuesday
    assert "## Happening Every Tuesday\n\n**Trivia/Game Night**\n\nTrivia" in tuesday


def test_uses_fixed_category_order_and_one_blank_line_between_blocks(tmp_path: Path) -> None:
    weekly = _write(
        tmp_path / "weekly.csv",
        """Date,Category,Event Name,Final Post Ready
07/27/2026,Faith Based,Faith,Faith listing
07/27/2026,Events/Hangouts,Hangout,Hangout listing
""",
    )
    recurring = _write(
        tmp_path / "recurring.csv",
        "Days of the Week,Category,Event Name,Final Post Ready\n",
    )

    output = build_weekly_reddit_post(
        load_weekly_export(weekly),
        load_recurring_export(recurring),
        week_start=date(2026, 7, 27),
    )

    assert output.index("**Events/Hangouts**") < output.index("**Faith Based**")
    assert "**Events/Hangouts**\n\nHangout listing" in output
    assert "Hangout listing\n\n**Faith Based**" in output
    assert "\n\n\n" not in output


def test_rejects_wrong_export_before_publishing(tmp_path: Path) -> None:
    wrong = _write(
        tmp_path / "wrong.csv",
        "Date,Category,Event Name\n07/27/2026,Events/Hangouts,Missing formula\n",
    )

    with pytest.raises(RedditPublishingError, match="wrong Notion export"):
        load_weekly_export(wrong)


def test_ordinal_recurring_rule_requires_dated_occurrence(tmp_path: Path) -> None:
    recurring = _write(
        tmp_path / "recurring.csv",
        """Days of the Week,Category,Event Name,Final Post Ready
3rd Wednesdays,Events/Hangouts,Monthly Club,Monthly Club listing
""",
    )

    with pytest.raises(RedditPublishingError, match="not an every-week schedule"):
        load_recurring_export(recurring)


def test_week_start_must_be_monday() -> None:
    with pytest.raises(RedditPublishingError, match="must be a Monday"):
        build_weekly_reddit_post([], [], week_start=date(2026, 7, 28))
