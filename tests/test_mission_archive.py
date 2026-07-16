import json
from pathlib import Path

from src.mission_archive import write_mission_artifacts
from src.mission_control import build_mission_control_report


def test_writes_stable_latest_and_timestamped_mission_archive(tmp_path: Path) -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[],
        counts={"review": 0, "rejected": 0},
        generated_at="2026-07-15T19:42:03+00:00",
    )

    outputs = write_mission_artifacts(
        report,
        latest_dir=tmp_path / "latest",
        archive_dir=tmp_path / "archive",
    )

    assert outputs["latest_dashboard"] == tmp_path / "latest" / "dashboard.html"
    assert outputs["latest_flight_recorder"] == tmp_path / "latest" / "flight_recorder.json"
    assert outputs["archive_dashboard"] == (
        tmp_path / "archive" / "MC-2026-029_20260715T194203Z" / "dashboard.html"
    )
    assert outputs["archive_flight_recorder"].exists()

    payload = json.loads(outputs["archive_flight_recorder"].read_text(encoding="utf-8"))
    assert payload["mission_id"] == "MC-2026-029"
    assert payload["project_name"] == "Mid-Columbia Mission Control"
