"""Publish weekly Reddit artifacts using live Notion recurring-event rows."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from src.notion_live import DEFAULT_WEEKLY_DATA_SOURCE_ID, fetch_live_weekly_rows
from tools.publish_reddit_live import main as publish_main


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--notion-api-key-env", default="NOTION_API_KEY")
    parser.add_argument("--notion-data-source-id", default=DEFAULT_WEEKLY_DATA_SOURCE_ID)
    known, remaining = parser.parse_known_args()

    if "--notion-weekly-export" in remaining:
        parser.error("live Notion wrapper cannot be combined with --notion-weekly-export")

    token = os.environ.get(known.notion_api_key_env, "").strip()
    if not token:
        parser.error(
            f"Notion API key not found in environment variable {known.notion_api_key_env}"
        )

    rows = fetch_live_weekly_rows(token, data_source_id=known.notion_data_source_id)
    temp_path: Path | None = None
    original_argv = sys.argv
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            encoding="utf-8",
            delete=False,
        ) as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
            temp_path = Path(handle.name)

        sys.argv = [
            "python -m tools.publish_reddit_live",
            *remaining,
            "--notion-weekly-export",
            str(temp_path),
        ]
        return publish_main()
    finally:
        sys.argv = original_argv
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
