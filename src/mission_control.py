"""Mission Control reporting for one production pipeline run.

This module is read-only. It summarizes existing pipeline results and artifacts without
changing harvesting, editorial policy, registries, or publisher output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.mission_identity import MISSION_FLOW, PROJECT_NAME, mission_id_for_week

DEFAULT_MISSION_CONTROL_DIR = Path("artifacts/mission_control")
DEFAULT_FLIGHT_RECORDER_PATH = DEFAULT_MISSION_CONTROL_DIR / "flight_recorder.json"
DEFAULT_DASHBOARD_PATH = DEFAULT_MISSION_CONTROL_DIR / "dashboard.html"


@dataclass(frozen=True)
class SourceHealthSummary:
    source: str
    status: str
    harvested: int = 0
    reason: str | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class MissionControlReport:
    project_name: str
    mission_id: str
    mission_flow: str
    generated_at: str
    week_start: str
    production_status: str
    ready_to_publish: bool
    captain_summary: str
    recommendation: str
    sources: tuple[SourceHealthSummary, ...]
    counts: dict[str, int]
    knowledge: dict[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    artifacts: dict[str, str] = field(default_factory=dict)
    regression: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sources"] = [asdict(item) for item in self.sources]
        payload["warnings"] = list(self.warnings)
        return payload


def build_mission_control_report(
    *,
    week_start: str,
    production_status: str,
    source_health: Iterable[SourceHealthSummary | Mapping[str, Any]],
    counts: Mapping[str, int],
    knowledge: Mapping[str, int] | None = None,
    warnings: Iterable[str] = (),
    artifacts: Mapping[str, str | Path] | None = None,
    regression: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> MissionControlReport:
    sources = tuple(_coerce_source(item) for item in source_health)
    clean_counts = {str(key): int(value) for key, value in counts.items()}
    clean_knowledge = {str(key): int(value) for key, value in (knowledge or {}).items()}
    clean_warnings = tuple(dict.fromkeys(str(item).strip() for item in warnings if str(item).strip()))
    clean_artifacts = {
        str(key): str(value)
        for key, value in (artifacts or {}).items()
        if str(value).strip()
    }
    clean_regression = dict(regression or {})

    required_source_failure = any(item.status.upper() not in {"OK", "PASS", "HEALTHY"} for item in sources)
    review_count = clean_counts.get("review", clean_counts.get("review_queue", 0))
    rejected_count = clean_counts.get("rejected", 0)
    regression_ok = clean_regression.get("passed", True) is not False
    ready = (
        production_status.upper() in {"OK", "PASS", "HEALTHY"}
        and not required_source_failure
        and review_count == 0
        and rejected_count == 0
        and regression_ok
    )
    captain_summary, recommendation = _captain_console(
        ready=ready,
        required_source_failure=required_source_failure,
        review_count=review_count,
        rejected_count=rejected_count,
        regression_ok=regression_ok,
        warning_count=len(clean_warnings),
    )

    return MissionControlReport(
        project_name=PROJECT_NAME,
        mission_id=mission_id_for_week(week_start),
        mission_flow=MISSION_FLOW,
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
        week_start=week_start,
        production_status=production_status,
        ready_to_publish=ready,
        captain_summary=captain_summary,
        recommendation=recommendation,
        sources=sources,
        counts=clean_counts,
        knowledge=clean_knowledge,
        warnings=clean_warnings,
        artifacts=clean_artifacts,
        regression=clean_regression,
    )


def write_flight_recorder(report: MissionControlReport, path: Path = DEFAULT_FLIGHT_RECORDER_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def render_dashboard(report: MissionControlReport) -> str:
    status_class = "ready" if report.ready_to_publish else "hold"
    launch_text = "READY TO PUBLISH" if report.ready_to_publish else "HOLD FOR REVIEW"
    source_rows = "".join(
        f"<tr><td>{escape(item.source)}</td><td>{escape(item.status)}</td>"
        f"<td>{item.harvested}</td><td>{'' if item.duration_ms is None else item.duration_ms}</td>"
        f"<td>{escape(item.reason or '')}</td></tr>"
        for item in report.sources
    )
    count_cards = "".join(_metric_card(key, value) for key, value in report.counts.items())
    knowledge_cards = "".join(_metric_card(key, value) for key, value in report.knowledge.items())
    warnings = "".join(f"<li>{escape(item)}</li>" for item in report.warnings) or "<li>None</li>"
    artifacts = "".join(
        f"<li><strong>{escape(key)}</strong>: <code>{escape(value)}</code></li>"
        for key, value in report.artifacts.items()
    ) or "<li>None recorded</li>"
    regression = escape(json.dumps(report.regression, ensure_ascii=False, sort_keys=True))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(report.project_name)} — {escape(report.mission_id)}</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, Segoe UI, Arial, sans-serif; }}
body {{ margin: 0; background: #0b0f14; color: #e8edf2; }}
main {{ max-width: 1180px; margin: auto; padding: 32px 20px 60px; }}
h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 4rem); letter-spacing: .04em; }}
.sub {{ color: #9ca9b6; margin: 8px 0 24px; }}
.launch {{ padding: 18px 22px; border-radius: 12px; font-size: 1.25rem; font-weight: 800; }}
.launch.ready {{ background: #123d2a; border: 1px solid #2f9e67; }}
.launch.hold {{ background: #4b241e; border: 1px solid #d26a55; }}
.console {{ background: #151b23; border: 1px solid #29313c; border-radius: 12px; padding: 18px 22px; margin-top: 18px; }}
.console strong {{ color: #b8d8ff; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 18px 0 28px; }}
.card {{ background: #151b23; border: 1px solid #29313c; border-radius: 10px; padding: 16px; }}
.card b {{ display: block; font-size: 1.8rem; margin-top: 6px; }}
section {{ margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; background: #151b23; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #29313c; text-align: left; }}
th {{ color: #9ca9b6; font-size: .85rem; text-transform: uppercase; }}
code {{ color: #b8d8ff; overflow-wrap: anywhere; }}
</style>
</head>
<body><main>
<h1>{escape(report.project_name.upper())}</h1>
<p class="sub">{escape(report.mission_id)} · Week of {escape(report.week_start)} · {escape(report.mission_flow)} · Generated {escape(report.generated_at)}</p>
<div class="launch {status_class}">{launch_text} · {escape(report.production_status)}</div>
<div class="console"><h2>Captain's Console</h2><p><strong>Status:</strong> {escape(report.captain_summary)}</p><p><strong>Recommendation:</strong> {escape(report.recommendation)}</p></div>
<section><h2>Production</h2><div class="grid">{count_cards}</div></section>
<section><h2>Knowledge</h2><div class="grid">{knowledge_cards or '<div class="card">No knowledge metrics yet</div>'}</div></section>
<section><h2>Source Health</h2><table><thead><tr><th>Source</th><th>Status</th><th>Harvested</th><th>ms</th><th>Reason</th></tr></thead><tbody>{source_rows}</tbody></table></section>
<section><h2>Warnings</h2><ul>{warnings}</ul></section>
<section><h2>Regression</h2><code>{regression}</code></section>
<section><h2>Artifacts</h2><ul>{artifacts}</ul></section>
</main></body></html>"""


def write_dashboard(report: MissionControlReport, path: Path = DEFAULT_DASHBOARD_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard(report), encoding="utf-8", newline="\n")
    return path


def _captain_console(
    *,
    ready: bool,
    required_source_failure: bool,
    review_count: int,
    rejected_count: int,
    regression_ok: bool,
    warning_count: int,
) -> tuple[str, str]:
    if ready:
        summary = "All launch gates are nominal."
        recommendation = "Publish the generated artifacts."
        if warning_count:
            recommendation = f"Review {warning_count} non-blocking warning(s), then publish."
        return summary, recommendation

    blockers: list[str] = []
    if required_source_failure:
        blockers.append("source health failure")
    if review_count:
        blockers.append(f"{review_count} review item(s)")
    if rejected_count:
        blockers.append(f"{rejected_count} rejected item(s)")
    if not regression_ok:
        blockers.append("regression failure")
    summary = "Launch held: " + ", ".join(blockers or ["production status is not nominal"]) + "."
    return summary, "Resolve the listed launch blockers and rerun the mission."


def _coerce_source(item: SourceHealthSummary | Mapping[str, Any]) -> SourceHealthSummary:
    if isinstance(item, SourceHealthSummary):
        return item
    return SourceHealthSummary(
        source=str(item.get("source") or item.get("source_name") or "Unknown"),
        status=str(item.get("status") or "UNKNOWN"),
        harvested=int(item.get("harvested") or item.get("count") or 0),
        reason=_optional_text(item.get("reason")),
        duration_ms=_optional_int(item.get("duration_ms")),
    )


def _metric_card(label: str, value: int) -> str:
    readable = escape(label.replace("_", " ").title())
    return f'<div class="card"><span>{readable}</span><b>{value}</b></div>'


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
