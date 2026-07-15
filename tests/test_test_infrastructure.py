import json
from pathlib import Path

from tests.builders import build_backlog, build_event
from tests.history_helpers import finalizer_paths, write_json, write_jsonl


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
