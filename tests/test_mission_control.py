import json
from pathlib import Path

from src.mission_control import (
    SourceHealthSummary,
    build_mission_control_report,
    render_dashboard,
    write_dashboard,
    write_flight_recorder,
)


def test_ready_only_when_launch_gates_are_clean() -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[SourceHealthSummary("AllEvents", "OK", harvested=12)],
        counts={
            "main": 8,
            "community": 4,
            "review": 5,
            "publication_blockers": 0,
            "editorial_reviews": 5,
            "rejected": 0,
        },
        regression={"passed": True, "tests": 466},
        generated_at="2026-07-15T12:00:00+00:00",
    )

    assert report.ready_to_publish is True
    assert "5 editorial item(s)" in report.recommendation

    held = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[SourceHealthSummary("AllEvents", "OK")],
        counts={"publication_blockers": 2, "editorial_reviews": 5, "rejected": 0},
        regression={"passed": True},
    )
    assert held.ready_to_publish is False
    assert "2 publication blocker(s)" in held.captain_summary


def test_legacy_review_count_remains_a_launch_gate() -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="OK",
        source_health=[SourceHealthSummary("AllEvents", "OK")],
        counts={"review": 1, "rejected": 0},
        regression={"passed": True},
    )
    assert report.ready_to_publish is False


def test_writes_json_and_dashboard_with_expected_operational_content(tmp_path: Path) -> None:
    report = build_mission_control_report(
        week_start="2026-07-13",
        production_status="DEGRADED",
        source_health=[{"source_name": "TriCityVibe", "status": "FAILED", "count": 0, "reason": "blocked"}],
        counts={
            "harvested": 31,
            "deduplicated": 28,
            "weekly": 12,
            "main": 5,
            "community": 3,
            "review": 3,
            "publication_blockers": 1,
            "editorial_reviews": 2,
            "rejected": 1,
        },
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
    assert "HOLD" in html
    assert "Mission Objectives" in html
    assert "Publication Blockers" in html
    assert "Editorial Review" in html
    assert "Pipeline Funnel" in html
    assert "badge failed" in html
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
