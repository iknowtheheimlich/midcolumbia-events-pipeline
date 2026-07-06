from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapters.tricity_vibe.parser import parse_events_html as parse_tricity_vibe
from adapters.mid_columbia_libraries.parser import parse_listing_html as parse_mcl


ADAPTERS = {
    "tricity_vibe": {
        "raw": Path("fixtures/tricity_vibe/raw_events.html"),
        "out": Path("fixtures/tricity_vibe/normalized_events.json"),
        "parser": parse_tricity_vibe,
    },
    "mid_columbia_libraries": {
        "raw": Path("fixtures/mid_columbia_libraries/raw_events.html"),
        "out": Path("fixtures/mid_columbia_libraries/normalized_events.json"),
        "parser": parse_mcl,
    },
}


def regenerate(name: str) -> int:
    adapter = ADAPTERS[name]
    raw_path = adapter["raw"]
    out_path = adapter["out"]

    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw fixture: {raw_path}")

    html = raw_path.read_text(encoding="utf-8")
    events = adapter["parser"](html)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(events, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"{name}: wrote {len(events)} events -> {out_path}")
    return len(events)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "adapter",
        choices=[*ADAPTERS.keys(), "all"],
        help="Adapter fixture to regenerate.",
    )
    args = parser.parse_args()

    names = ADAPTERS.keys() if args.adapter == "all" else [args.adapter]
    for name in names:
        regenerate(name)


if __name__ == "__main__":
    main()
