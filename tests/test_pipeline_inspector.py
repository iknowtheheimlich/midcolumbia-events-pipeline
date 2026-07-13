from pathlib import Path

import pytest

from src.pipeline_inspector import (
    matches_query,
    matching_rows,
    render_pipeline_inspector,
    write_pipeline_inspector,
)


def test_matches_query_searches_nested_event_data() -> None:
    event = {
        "title": "Summer Thursdays",
        "intelligence": {
            "venue": {"value": "Columbia Gardens", "confidence": 1.0, "reason": "registry_alias"}
        },
    }

    assert matches_query(event, "columbia gardens") is True
    assert matches_query(event, "summer thursdays") is True
    assert matches_query(event, "jazz jams") is False


def test_matching_rows_preserves_stage_order() -> None:
    rows = [
        {"title": "Other Event"},
        {"title": "Summer Thursdays", "source": "VisitTriCities"},
        {"title": "Summer Thursdays", "source": "AllEvents"},
    ]

    matches = matching_rows(rows, "summer thursdays")

    assert [row["source"] for row in matches] == ["VisitTriCities", "AllEvents"]


def test_render_pipeline_inspector_escapes_content_and_includes_final_line() -> None:
    html = render_pipeline_inspector(
        "Summer <Thursdays>",
        {
            "Collected source records": [
                {"title": "Summer <Thursdays>", "source": "VisitTriCities"}
            ],
            "Resolved occurrences": [],
        },
        rendered_lines=["Summer <Thursdays> | Columbia Gardens | 6-8p"],
    )

    assert "MCEI Pipeline Inspector" in html
    assert "Summer &lt;Thursdays&gt;" in html
    assert "Collected source records" in html
    assert "Final Reddit lines" in html
    assert "No matching records." in html


def test_write_pipeline_inspector_rejects_fixture_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="separate from fixtures"):
        write_pipeline_inspector(
            "Event",
            {"Stage": [{"title": "Event"}]},
            tmp_path / "fixtures" / "inspector.html",
        )
