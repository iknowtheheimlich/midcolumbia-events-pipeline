import json

import pytest

from tools.report_knowledge_drift import load_events


def test_load_events_supports_jsonl_history(tmp_path):
    path = tmp_path / "classified_events.jsonl"
    rows = [
        {"title": "One", "category": "Classes/Workshops"},
        {"title": "Two", "category": "Sports"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert load_events(path) == rows


def test_load_events_reports_invalid_jsonl_line(tmp_path):
    path = tmp_path / "classified_events.jsonl"
    path.write_text('{"title": "Valid"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        load_events(path)
