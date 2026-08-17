import json

from src.mission_trends import build_trend_summary, load_mission_history, write_mission_trends


def _record(generated_at, *, review=0, rejected=0, status="OK", ready=True, source_status="OK"):
    return {
        "mission_id": "MC-2026-07-20",
        "generated_at": generated_at,
        "week_start": "2026-07-20",
        "production_status": status,
        "ready_to_publish": ready,
        "counts": {
            "main": 10,
            "community": 20,
            "review": review,
            "rejected": rejected,
            "duplicates": 4,
        },
        "sources": [
            {"source": "AllEvents", "status": source_status, "harvested": 50},
            {"source": "NotionWeekly", "status": "OK", "harvested": 15},
        ],
        "warnings": ["warning"] if source_status != "OK" else [],
    }


def test_builds_chronological_points_and_deltas():
    summary = build_trend_summary(
        [
            _record("2026-07-16T12:00:00Z", review=9, rejected=2),
            _record("2026-07-16T13:00:00Z", review=6, rejected=1),
        ]
    )

    assert summary["mission_count"] == 2
    assert summary["latest"]["harvested"] == 65
    assert summary["changes_from_previous"]["review"] == -3
    assert summary["changes_from_previous"]["rejected"] == -1


def test_counts_degraded_missions_and_source_failures():
    summary = build_trend_summary(
        [
            _record("2026-07-16T12:00:00Z"),
            _record("2026-07-16T13:00:00Z", status="DEGRADED", ready=False, source_status="FAILED"),
        ]
    )

    assert summary["degraded_missions"] == 1
    assert summary["source_failure_frequency"] == {"AllEvents": 1}


def test_load_skips_invalid_recorders_and_sorts(tmp_path):
    later = tmp_path / "later"
    earlier = tmp_path / "earlier"
    broken = tmp_path / "broken"
    for directory in (later, earlier, broken):
        directory.mkdir()
    (later / "flight_recorder.json").write_text(json.dumps(_record("2026-07-16T14:00:00Z")), encoding="utf-8")
    (earlier / "flight_recorder.json").write_text(json.dumps(_record("2026-07-16T12:00:00Z")), encoding="utf-8")
    (broken / "flight_recorder.json").write_text("not json", encoding="utf-8")

    records = load_mission_history(tmp_path)

    assert [record["generated_at"] for record in records] == [
        "2026-07-16T12:00:00Z",
        "2026-07-16T14:00:00Z",
    ]


def test_writes_json_and_html_artifacts(tmp_path):
    archive = tmp_path / "archive" / "mission"
    archive.mkdir(parents=True)
    (archive / "flight_recorder.json").write_text(json.dumps(_record("2026-07-16T12:00:00Z", review=7)), encoding="utf-8")

    outputs = write_mission_trends(tmp_path / "archive", tmp_path / "trends")

    payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
    assert payload["latest"]["review"] == 7
    assert "MISSION ARCHIVE TRENDS" in outputs["html"].read_text(encoding="utf-8")
