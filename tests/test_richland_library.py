from __future__ import annotations

from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture
from src.pipeline import SourceBatch, run_pipeline


def test_richland_library_normalized_fixture_shape() -> None:
    events = load_json_fixture(Path("fixtures/richland_library/normalized_events.json"))

    assert len(events) == 12
    assert all(event["source"] == "RichlandLibrary" for event in events)
    assert all(event["city"] == "Richland" for event in events)
    assert all(event.get("source_event_id") for event in events)
    assert all(event.get("title") for event in events)
    assert all(event.get("start_date") for event in events)


def test_richland_library_pipeline_counts() -> None:
    events = load_json_fixture(Path("fixtures/richland_library/normalized_events.json"))
    result = run_pipeline([SourceBatch("RichlandLibrary", events)], deduplicate=True)

    assert result.counts == {
        "all_events": 12,
        "publisher_ready_events": 12,
        "recurrence_review_events": 0,
        "deduplicated_publisher_ready_events": 12,
        "duplicate_groups": 0,
        "skipped_low_quality_dedupe": 0,
    }
