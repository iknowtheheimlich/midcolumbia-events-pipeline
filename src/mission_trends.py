"""Build longitudinal analytics from archived Mission Control flight recorders."""

from __future__ import annotations

from collections import Counter
from html import escape
import json
from pathlib import Path
from typing import Any, Iterable

DEFAULT_ARCHIVE_DIR = Path("artifacts/mission_control/archive")
DEFAULT_TRENDS_DIR = Path("artifacts/mission_control/trends")


def load_mission_history(archive_dir: Path = DEFAULT_ARCHIVE_DIR) -> list[dict[str, Any]]:
    """Load valid archived flight recorders in chronological order."""
    records: list[dict[str, Any]] = []
    if not archive_dir.exists():
        return records

    for path in archive_dir.glob("*/flight_recorder.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        payload = dict(payload)
        payload["archive_path"] = str(path)
        records.append(payload)

    return sorted(records, key=lambda item: str(item.get("generated_at") or ""))


def build_trend_summary(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Reduce mission records into chart-ready points and operational summaries."""
    points: list[dict[str, Any]] = []
    source_failures: Counter[str] = Counter()

    for record in records:
        counts = record.get("counts") if isinstance(record.get("counts"), dict) else {}
        sources = record.get("sources") if isinstance(record.get("sources"), list) else []
        failed_sources = [
            str(source.get("source") or "Unknown")
            for source in sources
            if isinstance(source, dict)
            and str(source.get("status") or "UNKNOWN").upper() not in {"OK", "PASS", "HEALTHY"}
        ]
        source_failures.update(failed_sources)
        harvested = sum(
            int(source.get("harvested") or 0)
            for source in sources
            if isinstance(source, dict)
        )
        points.append(
            {
                "mission_id": str(record.get("mission_id") or "Unknown"),
                "generated_at": str(record.get("generated_at") or ""),
                "week_start": str(record.get("week_start") or ""),
                "production_status": str(record.get("production_status") or "UNKNOWN"),
                "ready_to_publish": bool(record.get("ready_to_publish")),
                "harvested": harvested,
                "main": _count(counts, "main", "main_events"),
                "community": _count(counts, "community", "community_events"),
                "review": _count(counts, "review", "review_queue"),
                "rejected": _count(counts, "rejected"),
                "duplicates": _count(counts, "duplicates", "duplicate_events"),
                "warnings": len(record.get("warnings") or []),
                "failed_sources": failed_sources,
                "archive_path": str(record.get("archive_path") or ""),
            }
        )

    latest = points[-1] if points else None
    previous = points[-2] if len(points) > 1 else None
    return {
        "schema_version": 1,
        "mission_count": len(points),
        "ready_missions": sum(1 for point in points if point["ready_to_publish"]),
        "degraded_missions": sum(1 for point in points if point["failed_sources"]),
        "latest": latest,
        "changes_from_previous": _changes(latest, previous),
        "source_failure_frequency": dict(source_failures.most_common()),
        "points": points,
    }


def write_mission_trends(
    archive_dir: Path = DEFAULT_ARCHIVE_DIR,
    output_dir: Path = DEFAULT_TRENDS_DIR,
) -> dict[str, Path]:
    """Write stable JSON and HTML trend artifacts."""
    summary = build_trend_summary(load_mission_history(archive_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "mission_trends.json"
    html_path = output_dir / "mission_trends.html"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_mission_trends(summary), encoding="utf-8", newline="\n")
    return {"json": json_path, "html": html_path}


def render_mission_trends(summary: dict[str, Any]) -> str:
    points = summary.get("points") or []
    latest = summary.get("latest") or {}
    changes = summary.get("changes_from_previous") or {}
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(point['generated_at']))}</td>"
        f"<td>{escape(str(point['production_status']))}</td>"
        f"<td>{point['harvested']}</td><td>{point['main']}</td><td>{point['community']}</td>"
        f"<td>{point['review']}</td><td>{point['rejected']}</td><td>{point['duplicates']}</td>"
        f"<td>{escape(', '.join(point['failed_sources']) or 'None')}</td>"
        "</tr>"
        for point in reversed(points)
    ) or '<tr><td colspan="9">No archived missions yet.</td></tr>'
    change_cards = "".join(
        f'<div class="card"><span>{escape(key.replace("_", " ").title())}</span><b>{value:+d}</b></div>'
        for key, value in changes.items()
    ) or '<div class="card">No previous mission available for comparison.</div>'
    failure_rows = "".join(
        f"<tr><td>{escape(source)}</td><td>{count}</td></tr>"
        for source, count in (summary.get("source_failure_frequency") or {}).items()
    ) or '<tr><td colspan="2">None recorded</td></tr>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mission Archive Trends</title><style>
:root {{ color-scheme: dark; font-family: Inter, Segoe UI, Arial, sans-serif; }}
body {{ margin:0; background:#0b0f14; color:#e8edf2; }} main {{ max-width:1200px; margin:auto; padding:32px 20px 60px; }}
h1 {{ margin-bottom:4px; }} .sub {{ color:#9ca9b6; }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:18px 0; }}
.card {{ background:#151b23; border:1px solid #29313c; border-radius:10px; padding:16px; }} .card b {{ display:block; font-size:1.8rem; margin-top:6px; }}
table {{ width:100%; border-collapse:collapse; background:#151b23; margin-top:12px; }} th,td {{ padding:10px 12px; border-bottom:1px solid #29313c; text-align:left; }}
th {{ color:#9ca9b6; font-size:.82rem; text-transform:uppercase; }} section {{ margin-top:30px; }}
</style></head><body><main>
<h1>MISSION ARCHIVE TRENDS</h1><p class="sub">{summary.get('mission_count', 0)} archived mission(s) · latest {escape(str(latest.get('generated_at') or 'none'))}</p>
<section><h2>Fleet Health</h2><div class="grid">
<div class="card"><span>Ready Missions</span><b>{summary.get('ready_missions', 0)}</b></div>
<div class="card"><span>Degraded Missions</span><b>{summary.get('degraded_missions', 0)}</b></div>
<div class="card"><span>Latest Review Queue</span><b>{latest.get('review', 0)}</b></div>
<div class="card"><span>Latest Rejected</span><b>{latest.get('rejected', 0)}</b></div>
</div></section>
<section><h2>Change From Previous Mission</h2><div class="grid">{change_cards}</div></section>
<section><h2>Mission History</h2><table><thead><tr><th>Generated</th><th>Status</th><th>Harvested</th><th>Main</th><th>Community</th><th>Review</th><th>Rejected</th><th>Duplicates</th><th>Failed Sources</th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>Source Failure Frequency</h2><table><thead><tr><th>Source</th><th>Missions Failed</th></tr></thead><tbody>{failure_rows}</tbody></table></section>
</main></body></html>"""


def _count(counts: dict[str, Any], *keys: str) -> int:
    for key in keys:
        if key in counts:
            try:
                return int(counts[key])
            except (TypeError, ValueError):
                return 0
    return 0


def _changes(latest: dict[str, Any] | None, previous: dict[str, Any] | None) -> dict[str, int]:
    if latest is None or previous is None:
        return {}
    keys = ("harvested", "main", "community", "review", "rejected", "duplicates", "warnings")
    return {key: int(latest[key]) - int(previous[key]) for key in keys}
