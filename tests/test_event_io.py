import json
from pathlib import Path

import pytest

from src.event_io import EVENT_LIST_KEYS, load_event_records


def test_loads_top_level_json_list(tmp_path: Path) -> None:
    path = tmp_path / "events.json"
    path.write_text(json.dumps([{"event_id": "1"}, "ignore"]), encoding="utf-8")
    assert load_event_records(path) == [{"event_id": "1"}]


def test_loads_every_supported_envelope_key(tmp_path: Path) -> None:
    for key in EVENT_LIST_KEYS:
        path = tmp_path / f"{key}.json"
        path.write_text(json.dumps({key: [{"event_id": key}]}), encoding="utf-8")
        assert load_event_records(path) == [{"event_id": key}]


def test_loads_jsonl_and_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"event_id":"1"}\n\n{"event_id":"2"}\n', encoding="utf-8")
    assert [row["event_id"] for row in load_event_records(path)] == ["1", "2"]


def test_invalid_jsonl_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"event_id":"1"}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_event_records(path)


def test_jsonl_requires_objects(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('[1, 2, 3]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Expected object"):
        load_event_records(path)
