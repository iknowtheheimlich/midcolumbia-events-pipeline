"""Probe the current Richland LibCal site without changing fixtures.

Attempt_23_Richland_Live_Fetch
"""

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
FORM_RE = re.compile(r'<form\b(?P<attrs>[^>]*)>', re.IGNORECASE)
ACTION_RE = re.compile(r'action=["\'](?P<action>[^"\']+)["\']', re.IGNORECASE)
MARKERS = (
    "ajax/calendar",
    "fullcalendar",
    "s-lc-",
    "event/",
    "calendar?",
    "cal[]",
    "cid=",
    "data-event",
)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        BASE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            final_url = response.geturl()
            status = response.status
            headers = str(response.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        final_url = exc.geturl()
        status = exc.code
        headers = str(exc.headers)

    (OUTPUT_DIR / "root.html").write_text(body, encoding="utf-8")
    (OUTPUT_DIR / "headers.txt").write_text(headers, encoding="utf-8")

    links = sorted({urljoin(final_url, match.group("href")) for match in LINK_RE.finditer(body)})
    calendar_links = [
        link for link in links
        if any(token in link.lower() for token in ("calendar", "event", "libcal", "ajax"))
    ]
    (OUTPUT_DIR / "links.txt").write_text("\n".join(calendar_links) + "\n", encoding="utf-8")

    scripts = sorted({urljoin(final_url, match.group("src")) for match in SCRIPT_RE.finditer(body)})
    (OUTPUT_DIR / "scripts.txt").write_text("\n".join(scripts) + "\n", encoding="utf-8")

    forms: list[str] = []
    for match in FORM_RE.finditer(body):
        attrs = match.group("attrs")
        action_match = ACTION_RE.search(attrs)
        action = urljoin(final_url, action_match.group("action")) if action_match else "(no action)"
        forms.append(f"{action} | {attrs.strip()}")
    (OUTPUT_DIR / "forms.txt").write_text("\n".join(forms) + "\n", encoding="utf-8")

    snippets: list[str] = []
    lower = body.lower()
    for marker in MARKERS:
        start = 0
        while True:
            index = lower.find(marker.lower(), start)
            if index < 0:
                break
            left = max(0, index - 180)
            right = min(len(body), index + 320)
            snippets.append(f"--- {marker} @ {index} ---\n{body[left:right]}\n")
            start = index + len(marker)
            if len(snippets) >= 120:
                break
        if len(snippets) >= 120:
            break
    (OUTPUT_DIR / "snippets.txt").write_text("\n".join(snippets), encoding="utf-8")

    print(f"Status: {status}")
    print(f"Requested: {BASE_URL}")
    print(f"Final URL: {final_url}")
    print(f"Body bytes: {len(body.encode('utf-8'))}")
    print(f"Calendar-like links: {len(calendar_links)}")
    print(f"Scripts: {len(scripts)}")
    print(f"Forms: {len(forms)}")
    print(f"Marker snippets: {len(snippets)}")
    for link in calendar_links[:20]:
        print(f"  {link}")
    print(f"Saved probe output under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
