"""Generate the publish-ready weekly Reddit .txt artifact from two Notion exports."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.reddit_weekly_publisher import RedditPublishingError, write_weekly_reddit_post


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "weekly_csv",
        type=Path,
        help="Reddit publishing-view CSV containing dated and date-range events",
    )
    parser.add_argument(
        "recurring_csv",
        type=Path,
        help="Recurring Templates Library CSV containing Days of the Week",
    )
    parser.add_argument(
        "--week-start",
        required=True,
        help="Monday for the publication week (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output .txt path (default: artifacts/Weekly_Reddit_Post_YYYY-MM-DD.txt)",
    )
    args = parser.parse_args()

    try:
        week_start = datetime.strptime(args.week_start, "%Y-%m-%d").date()
        output = args.output or Path(
            f"artifacts/Weekly_Reddit_Post_{week_start.isoformat()}.txt"
        )
        write_weekly_reddit_post(
            args.weekly_csv,
            args.recurring_csv,
            output,
            week_start=week_start,
        )
    except (ValueError, RedditPublishingError) as exc:
        parser.error(str(exc))

    print(output)


if __name__ == "__main__":
    main()
