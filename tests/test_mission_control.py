import json
from pathlib import Path

from src.mission_control import (
    SourceHealthSummary,
    build_mission_control_report,
    render_dashboard,
    write_dashboard,
    write_flight_recorder,
)


def test_ready_only_when_sources_reviews_rejections_and_regression_are_clean() -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[SourceHealthSummary("AllEvents", "OK", harvested=12)],
        counts={"main": 8, "community": 4, "review": 0, "rejected": 0},
        regression={"passed": True, "tests": 466},
        generated_at="2026-07-15T12:00:00+00:00",
    )

    assert report.ready_to_publish is True

    held = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[SourceHealthSummary("AllEvents", "FAILED", reason="timeout")],
        counts={"review": 0, "rejected": 0},
        regression={"passed": True},
    )
    assert held.ready_to_publish is False


def test_writes_json_and_dashboard_with_expected_operational_content(tmp_path: Path) -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="DEGRADED",
        source_health=[{"source_name": "TriCityVibe", "status": "FAILED", "count": 0, "reason": "blocked"}],
        counts={"harvested": 31, "review_queue": 2, "rejected": 1},
        knowledge={"venues": 373, "hosts": 327, "artist_candidates": 6},
        warnings=["New venue detected", "New venue detected"],
        artifacts={"main": Path("artifacts/reddit/Main_Events_Post.txt")},
        regression={"passed": True, "tests": 466},
        generated_at="2026-07-15T12:00:00+00:00",
    )

    recorder = write_flight_recorder(report, tmp_path / "flight_recorder.json")
    dashboard = write_dashboard(report, tmp_path / "dashboard.html")

    payload = json.loads(recorder.read_text(encoding="utf-8"))
    html = dashboard.read_text(encoding="utf-8")
    assert payload["ready_to_publish"] is False
    assert payload["warnings"] == ["New venue detected"]
    assert "HOLD FOR REVIEW" in html
    assert "TriCityVibe" in html
    assert "373" in html
    assert "Main_Events_Post.txt" in html


def test_dashboard_escapes_untrusted_text() -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[{"source": "<script>", "status": "OK"}],
        counts={},
        warnings=["<b>unsafe</b>"],
    )

    html = render_dashboard(report)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in html
