import ast
import json
from pathlib import Path

from tests.builders import build_backlog, build_event
from tests.history_helpers import finalizer_paths, write_json, write_jsonl
from tools.finalize_weekly_run import finalize_weekly_run


def test_event_builder_applies_overrides() -> None:
    event = build_event("9", category="Classes/Workshops", venue="Art YOUR Way")
    assert event["event_id"] == "9"
    assert event["category"] == "Classes/Workshops"
    assert event["venue"] == "Art YOUR Way"


def test_backlog_builder_uses_decision_key() -> None:
    backlog = build_backlog("7", category="Music/Comedy", appearances=4)
    assert backlog["7|Music/Comedy"]["appearances"] == 4


def test_json_and_jsonl_helpers_round_trip(tmp_path: Path) -> None:
    json_path = write_json(tmp_path / "data.json", [{"id": 1}])
    jsonl_path = write_jsonl(tmp_path / "data.jsonl", [{"id": 1}, {"id": 2}])
    assert json.loads(json_path.read_text(encoding="utf-8")) == [{"id": 1}]
    assert [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()] == [
        {"id": 1},
        {"id": 2},
    ]


def test_finalizer_paths_are_isolated_under_tmp_path(tmp_path: Path) -> None:
    paths = finalizer_paths(tmp_path)
    assert set(paths) == {
        "history_path",
        "review_ledger_path",
        "review_backlog_path",
        "throughput_history_path",
        "snapshots_dir",
        "artifacts_dir",
    }
    assert all(tmp_path in path.parents or path == tmp_path for path in paths.values())


def test_finalizer_cannot_escape_temporary_boundary(tmp_path: Path, monkeypatch) -> None:
    sentinel_root = tmp_path / "repository"
    sentinel_history = sentinel_root / "history"
    sentinel_history.mkdir(parents=True)
    sentinels = {
        sentinel_history / "classified_events.jsonl": "production classified history\n",
        sentinel_history / "classification_reviews.jsonl": "production review ledger\n",
        sentinel_history / "review_backlog.json": "production review backlog\n",
        sentinel_history / "review_backlog_throughput.jsonl": "production throughput history\n",
    }
    for path, content in sentinels.items():
        path.write_text(content, encoding="utf-8")

    monkeypatch.chdir(sentinel_root)
    boundary = tmp_path / "isolated"
    paths = finalizer_paths(boundary)
    input_path = write_json(boundary / "events.json", [build_event()])

    first = finalize_weekly_run(input_path, **finalizer_paths(boundary), run_reports=False)
    second = finalize_weekly_run(input_path, **finalizer_paths(boundary), run_reports=False)

    writable_results = (
        "history_path",
        "health_report",
        "review_operations_config",
        "review_backlog_path",
        "review_backlog_report",
        "review_backlog_throughput_report",
        "review_sla_report",
        "review_capacity_report",
        "review_operational_metrics",
        "review_batch_path",
        "pipeline_health_report",
        "pipeline_health_json",
    )
    for key in writable_results:
        output = Path(second[key]).resolve()
        assert boundary.resolve() in output.parents

    throughput_rows = paths["throughput_history_path"].read_text(encoding="utf-8").splitlines()
    assert len(throughput_rows) == 2
    assert all(json.loads(row)["run_date"] for row in throughput_rows)
    assert paths["review_backlog_path"].exists()
    assert first["snapshot_path"] is None
    assert second["snapshot_path"] is not None
    assert Path(second["snapshot_path"]).parent == paths["snapshots_dir"]
    assert list(paths["snapshots_dir"].glob("*.jsonl")) == [Path(second["snapshot_path"])]
    for path, content in sentinels.items():
        assert path.read_text(encoding="utf-8") == content
    assert not (sentinel_root / "artifacts").exists()
    assert not (sentinel_history / "snapshots").exists()


def test_finalizer_test_calls_never_supply_partial_path_sets() -> None:
    tests_dir = Path(__file__).parent
    writable_path_names = {
        "history_path",
        "review_ledger_path",
        "review_backlog_path",
        "throughput_history_path",
        "snapshots_dir",
        "artifacts_dir",
    }
    violations: list[str] = []

    for test_file in sorted(tests_dir.glob("test_*.py")):
        tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "finalize_weekly_run":
                continue
            uses_helper = any(
                keyword.arg is None
                and isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "finalizer_paths"
                for keyword in node.keywords
            )
            explicit_paths = {keyword.arg for keyword in node.keywords if keyword.arg in writable_path_names}
            if not uses_helper and explicit_paths != writable_path_names:
                missing = ", ".join(sorted(writable_path_names - explicit_paths))
                violations.append(f"{test_file.name}:{node.lineno} missing {missing}")

    assert not violations, "Partial finalize_weekly_run path configuration:\n" + "\n".join(violations)
