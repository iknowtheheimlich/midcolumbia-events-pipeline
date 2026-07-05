from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import save_json_fixture
from adapters.richland_library.parser import parse_monthly_html

DEFAULT_INPUT = Path("fixtures/richland_library/raw_events.html")
DEFAULT_OUTPUT = Path("fixtures/richland_library/normalized_events.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    fixture_text = args.input.read_text(encoding="utf-8")
    events = parse_monthly_html(fixture_text)
    save_json_fixture(args.output, events)

    print(f"Normalized events: {len(events)}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()