from __future__ import annotations

from src.pipeline import SourceBatch, combine_source_batches
from src.text_normalization import normalize_event, normalize_text


def test_repairs_common_windows_1252_mojibake() -> None:
    assert normalize_text("Farm to Fork â€“ Market Tour") == "Farm to Fork – Market Tour"
    assert normalize_text("Chefâ€™s Table") == "Chef’s Table"
    assert normalize_text("Music â€” Wine â€¦ More") == "Music — Wine … More"


def test_preserves_correct_unicode_and_plain_text() -> None:
    values = [
        "Farm to Fork – Market Tour",
        "Chef’s Table",
        "Café con música",
        "Tri-Cities Summer Festival",
        "Emoji stays intact 🎉",
    ]

    assert [normalize_text(value) for value in values] == values


def test_normalizes_nested_event_values_without_mutating_input() -> None:
    event = {
        "title": "Farm to Fork â€“ Market Tour",
        "description": "Chefâ€™s demo",
        "metadata": {"labels": ["Food â€” Drink", "Correct – dash"]},
    }

    normalized = normalize_event(event)

    assert normalized["title"] == "Farm to Fork – Market Tour"
    assert normalized["description"] == "Chef’s demo"
    assert normalized["metadata"]["labels"] == ["Food — Drink", "Correct – dash"]
    assert event["title"] == "Farm to Fork â€“ Market Tour"


def test_pipeline_normalizes_before_downstream_processing() -> None:
    event = {
        "title": "Farm to Fork â€“ Market Tour",
        "start_date": "2026-07-25",
        "start_time": "09:45",
        "venue": "Imbibe",
        "city": "Pasco",
        "event_kind": "single",
        "is_series": False,
    }

    combined = combine_source_batches([SourceBatch("VisitTriCities", [event])])

    assert combined[0]["title"] == "Farm to Fork – Market Tour"
    assert combined[0]["source"] == "VisitTriCities"
