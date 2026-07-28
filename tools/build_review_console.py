"""Build the browser-based editorial review console.

Example:
    python -m tools.build_review_console \
        --review-training artifacts/review/Review_Training.json \
        --main-post artifacts/reddit/Main_Events_Post.txt \
        --community-post artifacts/reddit/Community_Events_Post.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.review_console import build_review_console
from src.review_trainer import DEFAULT_REVIEW_TRAINING_PATH

DEFAULT_OUTPUT = Path("artifacts/review/Review_Console.html")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-training", type=Path, default=DEFAULT_REVIEW_TRAINING_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--main-post", type=Path)
    parser.add_argument("--community-post", type=Path)
    args = parser.parse_args()

    if not args.review_training.exists():
        parser.error(f"review training artifact not found: {args.review_training}")

    published_paths = [path for path in (args.main_post, args.community_post) if path]
    for path in published_paths:
        if not path.exists():
            parser.error(f"published Reddit artifact not found: {path}")

    output = build_review_console(
        args.review_training,
        args.output,
        published_paths=published_paths,
    )
    print(f"Review console: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
