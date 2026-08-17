"""Build Mission Archive trend artifacts from local flight recorders."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.mission_trends import DEFAULT_ARCHIVE_DIR, DEFAULT_TRENDS_DIR, write_mission_trends


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TRENDS_DIR)
    args = parser.parse_args()

    outputs = write_mission_trends(args.archive_dir, args.output_dir)
    print(f"Mission trends JSON: {outputs['json']}")
    print(f"Mission trends HTML: {outputs['html']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
