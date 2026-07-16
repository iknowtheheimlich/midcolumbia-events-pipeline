from src.mission_control import SourceHealthSummary, build_mission_control_report, render_dashboard
from src.mission_identity import mission_id_for_week


def test_mission_id_uses_zero_padded_iso_week() -> None:
    assert mission_id_for_week("2026-07-13") == "MC-2026-029"


def test_report_carries_project_identity_and_captain_console() -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[SourceHealthSummary("AllEvents", "OK", harvested=12)],
        counts={"review": 0, "rejected": 0},
        regression={"passed": True},
        generated_at="2026-07-15T12:00:00+00:00",
    )

    assert report.project_name == "Mid-Columbia Mission Control"
    assert report.mission_id == "MC-2026-029"
    assert report.captain_summary == "All launch gates are nominal."
    assert report.recommendation == "Publish the generated artifacts."

    html = render_dashboard(report)
    assert "MID-COLUMBIA MISSION CONTROL" in html
    assert "MC-2026-029" in html
    assert "Captain's Console" in html


def test_captain_console_names_blockers() -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="DEGRADED",
        source_health=[SourceHealthSummary("AllEvents", "FAILED")],
        counts={"review": 2, "rejected": 1},
        regression={"passed": False},
    )

    assert report.ready_to_publish is False
    assert "source health failure" in report.captain_summary
    assert "2 review item(s)" in report.captain_summary
    assert "1 rejected item(s)" in report.captain_summary
    assert "regression failure" in report.captain_summary
