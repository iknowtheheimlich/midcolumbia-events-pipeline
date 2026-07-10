"""Probe the current Richland LibCal site without changing fixtures."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from adapters.richland_library.config import BASE_URL


OUTPUT_DIR = Path("generated/probes/richland_libcal")
LINK_RE = re.compile(r'href=["\'](?P<href>[^"\']+)["\']', re.IGNORECASE)
SCRIPT_RE = re.compile(r'src=["\'](?P<src>[^"\']+)["\']', re.IGNORECASE)
ENDPOINT_RE = re.compile(
    r'(?P<value>(?:https?:)?//[^"\']+|/[A-Za-z0-9_./?=&%\[\]-]+)',
    re.IGNORECASE,
)
MARKERS = ("ajax", "eventsource", "events:", "url:", "calendar", "feed", "process_")


def fetch_text(url: str) -> tuple[str, str, int]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36",
            "Accept": "text/html,application/javascript,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace"), response.geturl(), response.status
    except urllib.error.HTTPError as exc:
        return exc.read().decode("utf-8", errors="replace"), exc.geturl(), exc.code


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    body, final_url, status = fetch_text(BASE_URL)
    (OUTPUT_DIR / "root.html").write_text(body, encoding="utf-8")

    links = sorted({urljoin(final_url, match.group("href")) for match in LINK_RE.finditer(body)})
    scripts = sorted({urljoin(final_url, match.group("src")) for match in SCRIPT_RE.finditer(body)})
    (OUTPUT_DIR / "links.txt").write_text("\n".join(links) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "scripts.txt").write_text("\n".join(scripts) + "\n", encoding="utf-8")

    reports: list[str] = []
    for index, script_url in enumerate(scripts, start=1):
        if not any(token in script_url.lower() for token in ("calendar", "event", "libcal")):
            continue
        script_body, resolved_url, script_status = fetch_text(script_url)
        safe_name = f"script_{index:02d}.js"
        (OUTPUT_DIR / safe_name).write_text(script_body, encoding="utf-8")

        values = sorted({match.group("value") for match in ENDPOINT_RE.finditer(script_body)})
        interesting = [
            value for value in values
            if any(token in value.lower() for token in ("ajax", "event", "calendar", "feed", "process_"))
        ]
        marker_hits = [marker for marker in MARKERS if marker.lower() in script_body.lower()]
        reports.append(
            f"[{script_status}] {resolved_url}\n"
            f"saved={safe_name}\n"
            f"markers={marker_hits}\n"
            + "\n".join(f"  {value}" for value in interesting[:80])
            + "\n"
        )

    (OUTPUT_DIR / "script_endpoints.txt").write_text("\n".join(reports), encoding="utf-8")

    print(f"Status: {status}")
    print(f"Final URL: {final_url}")
    print(f"Scripts inspected: {len(reports)}")
    print(f"Saved probe output under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
