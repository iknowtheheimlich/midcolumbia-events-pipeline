from pathlib import Path


def test_live_publisher_calls_mission_control_once() -> None:
    source = Path("tools/publish_reddit_live.py").read_text(encoding="utf-8")

    assert source.count("write_production_mission_control(") == 1
    assert source.count("build_review_triage_from_file(") == 1
    assert source.index("write_review_training_artifact(") < source.index("build_review_triage_from_file(")
    assert source.index("build_review_triage_from_file(") < source.index("write_production_mission_control(")
    assert 'print(f"Mission: {mission_report.mission_id}")' in source
    assert "Mission Control: {'READY TO PUBLISH' if mission_report.ready_to_publish else 'HOLD FOR REVIEW'}" in source
    assert 'print(f"Review triage (blockers first): {review_triage_outputs[\'report\']}")' in source


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
        '"review_triage_json"',
        '"review_triage_csv"',
        '"review_triage_report"',
    ):
        assert artifact_key in source
