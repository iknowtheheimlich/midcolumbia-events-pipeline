"""Probe Eventbrite search pages with a real browser session.

Attempt_24_Eventbrite

This tool is intentionally isolated from the normal pipeline. Eventbrite rejects
plain HTTP fetches, so the probe uses Playwright when available and saves only
untracked diagnostics under generated/probes/eventbrite_browser/.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from adapters.eventbrite.config import SEARCH_URLS


OUTPUT_ROOT = Path("generated/probes/eventbrite_browser")
EVENT_LINK_RE = re.compile(r"https://www\.eventbrite\.com/e/[^\"'?# ]+", re.IGNORECASE)


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Playwright is not installed.")
        print("Install it with:")
        print("  python -m pip install playwright")
        print("  python -m playwright install chromium")
        raise SystemExit(2)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1200},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            ),
        )

        for city, url in SEARCH_URLS.items():
            city_dir = OUTPUT_ROOT / city.lower()
            city_dir.mkdir(parents=True, exist_ok=True)
            page = context.new_page()
            responses: list[dict[str, object]] = []

            def record_response(response) -> None:  # type: ignore[no-untyped-def]
                content_type = response.headers.get("content-type", "")
                if any(token in response.url.lower() for token in ("search", "event", "graphql", "api")):
                    responses.append(
                        {
                            "status": response.status,
                            "url": response.url,
                            "content_type": content_type,
                        }
                    )

            page.on("response", record_response)
            response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(5_000)

            html = page.content()
            title = page.title()
            final_url = page.url
            status = response.status if response else None

            (city_dir / "page.html").write_text(html, encoding="utf-8")
            (city_dir / "responses.json").write_text(
                json.dumps(responses, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            page.screenshot(path=str(city_dir / "page.png"), full_page=True)

            links = sorted(
                {
                    urljoin(final_url, href)
                    for href in page.locator("a").evaluate_all(
                        "els => els.map(el => el.href).filter(Boolean)"
                    )
                    if "/e/" in href
                }
            )
            links.extend(EVENT_LINK_RE.findall(html))
            links = sorted(set(links))
            (city_dir / "event_links.txt").write_text("\n".join(links) + "\n", encoding="utf-8")

            state_markers = {
                "__NEXT_DATA__": "__NEXT_DATA__" in html,
                "application_ld_json": "application/ld+json" in html,
                "graphql": "graphql" in html.lower(),
                "event_card": "event-card" in html.lower(),
            }
            (city_dir / "markers.json").write_text(
                json.dumps(state_markers, indent=2) + "\n",
                encoding="utf-8",
            )

            line = (
                f"{city}: status={status} final={final_url} title={title!r} "
                f"bytes={len(html.encode('utf-8'))} event_links={len(links)} "
                f"responses={len(responses)} markers={state_markers}"
            )
            summary.append(line)
            print(line)
            page.close()

        context.close()
        browser.close()

    (OUTPUT_ROOT / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"Saved browser probe under: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
