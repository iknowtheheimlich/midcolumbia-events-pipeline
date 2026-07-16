"""Write stable and timestamped Mid-Columbia Mission Control artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.mission_control import MissionControlReport, write_dashboard, write_flight_recorder

DEFAULT_LATEST_DIR = Path("artifacts/mission_control/latest")
DEFAULT_ARCHIVE_DIR = Path("artifacts/mission_control/archive")


def write_mission_artifacts(
    report: MissionControlReport,
    *,
    latest_dir: Path = DEFAULT_LATEST_DIR,
    archive_dir: Path = DEFAULT_ARCHIVE_DIR,
) -> dict[str, Path]:
    """Write stable latest files and a unique timestamped mission archive."""
    stamp = _archive_stamp(report.generated_at)
    mission_dir = archive_dir / f"{report.mission_id}_{stamp}"

    outputs = {
        "latest_dashboard": write_dashboard(report, latest_dir / "dashboard.html"),
        "latest_flight_recorder": write_flight_recorder(
            report, latest_dir / "flight_recorder.json"
        ),
        "archive_dashboard": write_dashboard(report, mission_dir / "dashboard.html"),
        "archive_flight_recorder": write_flight_recorder(
            report, mission_dir / "flight_recorder.json"
        ),
    }
    return outputs


def _archive_stamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
