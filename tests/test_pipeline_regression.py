from __future__ import annotations

from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture
from src.pipeline import SourceBatch, run_pipeline


def test_three_source_pipeline_counts() -> None:
    batches = [
        SourceBatch(
            source_name="VisitTriCities",
            events=load_json_fixture(Path("fixtures/visit_tricities/normalized_events.json")),
        ),
        SourceBatch(
            source_name="LegacyUnifiedCSV",
            events=load_json_fixture(Path("fixtures/legacy/normalized_events.json")),
        ),
        SourceBatch(
            source_name="RichlandLibrary",
            events=load_json_fixture(Path("fixtures/richland_library/normalized_events.json")),
        ),
    ]

    result = run_pipeline(batches, deduplicate=True)

    assert result.counts == {
        "all_events": 123,
        "publisher_ready_events": 114,
        "recurrence_review_events": 9,
        "deduplicated_publisher_ready_events": 113,
        "duplicate_groups": 1,
        "skipped_low_quality_dedupe": 30,
    }
