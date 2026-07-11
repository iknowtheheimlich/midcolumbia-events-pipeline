"""Probe current Eventbrite public search pages without changing fixtures.

Attempt_24_Eventbrite

The probe records public HTML, JSON-LD blocks, likely application-state JSON,
and event-like links for each Tri-Cities search page. It does not register an
adapter or alter pipeline inputs.
"""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from adapters.eventbrite.config import SEARCH_URLS, USER_AGENT


OUTPUT_ROOT = Path("generated/probes/eventbrite")
SCRIPT_RE = re.compile(
    r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
TYPE_RE = re.compile(r'type=["\'](?P<type>[^"\']+)["\']', re.IGNORECASE)
ID_RE = re.compile(r'id=["\'](?P<id>[^"\']+)["\']', re.IGNORECASE)
LINK_RE = re.compile(r'href=["\'](?P<href>[^"\']+)["\']', re.IGNORECASE)
EVENT_URL_RE = re.compile(r"https?://(?:www\.)?eventbrite\.com/e/[^\s\"'<>]+", re.IGNORECASE)


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summaries: list[str] = []

    for city, url in SEARCH_URLS.items():
        city_dir = OUTPUT_ROOT / city.lower().replace(" ", "_")
        city_dir.mkdir(parents=True, exist_ok=True)

        status, final_url, headers, body = fetch(url)
        (city_dir / "page.html").write_text(body, encoding="utf-8")
        (city_dir / "headers.txt").write_text(headers, encoding="utf-8")

        json_blocks = extract_json_scripts(body, city_dir)
        event_links = extract_event_links(body, final_url)
        (city_dir / "event_links.txt").write_text("\n".join(event_links) + "\n", encoding="utf-8")

        summary = (
            f"{city}: status={status} final={final_url} bytes={len(body.encode('utf-8'))} "
            f"json_blocks={json_blocks} event_links={len(event_links)}"
        )
        summaries.append(summary)
        print(summary)
        for link in event_links[:8]:
            print(f"  {link}")

    (OUTPUT_ROOT / "summary.txt").write_text("\n".join(summaries) + "\n", encoding="utf-8")
    print(f"Saved probe output under: {OUTPUT_ROOT}")


def fetch(url: str) -> tuple[int, str, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return (
                response.status,
                response.geturl(),
                str(response.headers),
                response.read().decode(charset, errors="replace"),
            )
    except urllib.error.HTTPError as exc:
        return (
            exc.code,
            exc.geturl(),
            str(exc.headers),
            exc.read().decode("utf-8", errors="replace"),
        )


def extract_json_scripts(body: str, output_dir: Path) -> int:
    count = 0
    manifest: list[str] = []
    for index, match in enumerate(SCRIPT_RE.finditer(body), start=1):
        attrs = match.group("attrs")
        script_body = html.unescape(match.group("body").strip())
        script_type_match = TYPE_RE.search(attrs)
        script_id_match = ID_RE.search(attrs)
        script_type = script_type_match.group("type") if script_type_match else ""
        script_id = script_id_match.group("id") if script_id_match else ""

        looks_json = (
            "json" in script_type.lower()
            or script_id in {"__NEXT_DATA__", "__APOLLO_STATE__"}
            or script_body.startswith("{")
            or script_body.startswith("[")
        )
        if not looks_json or not script_body:
            continue

        count += 1
        filename = f"json_{count:02d}.json"
        parsed = False
        try:
            payload = json.loads(script_body)
            (output_dir / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            parsed = True
        except json.JSONDecodeError:
            filename = f"json_{count:02d}.txt"
            (output_dir / filename).write_text(script_body + "\n", encoding="utf-8")

        manifest.append(
            f"{filename} type={script_type or '(none)'} id={script_id or '(none)'} parsed={parsed} bytes={len(script_body.encode('utf-8'))}"
        )

    (output_dir / "json_manifest.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    return count


def extract_event_links(body: str, final_url: str) -> list[str]:
    links = {match.group(0).rstrip("\\") for match in EVENT_URL_RE.finditer(body)}
    for match in LINK_RE.finditer(body):
        absolute = urljoin(final_url, html.unescape(match.group("href")))
        if "/e/" in absolute and "eventbrite." in absolute:
            links.add(absolute)
    return sorted(links)


if __name__ == "__main__":
    main()
