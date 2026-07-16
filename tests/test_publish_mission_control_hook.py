from pathlib import Path


def test_live_publisher_calls_mission_control_once() -> None:
    source = Path("tools/publish_reddit_live.py").read_text(encoding="utf-8")

    assert source.count("write_production_mission_control(") == 1
    assert 'print(f"Mission: {mission_report.mission_id}")' in source
    assert "Mission Control: {'READY TO PUBLISH' if mission_report.ready_to_publish else 'HOLD FOR REVIEW'}" in source


def test_live_publisher_records_core_artifact_paths() -> None:
    source = Path("tools/publish_reddit_live.py").read_text(encoding="utf-8")

    for artifact_key in (
        '"main_reddit"',
        '"community_reddit"',
        '"publisher_audit"',
        '"event_knowledge_graph"',
        '"source_metrics"',
        '"harvest_telemetry"',
        '"review_training"',
    ):
        assert artifact_key in source
