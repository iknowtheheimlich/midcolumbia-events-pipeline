"""Fetch Mid-Columbia Libraries events HTML fixture."""

from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

from adapters.mcl.config import EVENTS_URL

OUTPUT_PATH = Path("fixtures/mcl/raw_events.html")


def main() -> None:
    request = Request(
        EVENTS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 Mid-Columbia Events Pipeline fixture fetcher"
        },
    )

    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Bytes: {len(html.encode('utf-8'))}")


if __name__ == "__main__":
    main()