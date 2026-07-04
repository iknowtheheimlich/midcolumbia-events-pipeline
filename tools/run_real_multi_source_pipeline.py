"""Run Visit Tri-Cities and Allevents fixtures through the unified pipeline."""

from __future__ import annotations

from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture, save_json_fixture
from adapters.visit_tricities.config import SOURCE_NAME as VTC_SOURCE_NAME
from src.pipeline import SourceBatch, run_pipeline

VTC_INPUT = Path("fixtures/visit_tricities/normalized_events.json")
ALLEVENTS_INPUT = Path("fixtures/allevents/normalized_events.json")
READY_OUTPUT = Path("fixtures/real_multi_source/publisher_ready_events.json")
REVIEW_OUTPUT = Path("fixtures/real_multi_source/series_review_queue.json")


def main() -> None:
    vtc_events = load_json_fixture(VTC_INPUT)
    allevents_events = load_json_fixture(ALLEVENTS_INPUT)

    if not isinstance(vtc_events, list):
        raise TypeError("Visit Tri-Cities fixture must be a list")
    if not isinstance(allevents_events, list):
        raise TypeError("Allevents fixture must be a list")

    result = run_pipeline(
        [
            SourceBatch(source_name=VTC_SOURCE_NAME, events=vtc_events),
            SourceBatch(source_name="Allevents", events=allevents_events),
        ]
    )

    save_json_fixture(READY_OUTPUT, result.publisher_ready_events)
    save_json_fixture(REVIEW_OUTPUT, result.recurrence_review_events)

    print(result.counts)
    print(f"Publisher-ready: {READY_OUTPUT}")
    print(f"Series review: {REVIEW_OUTPUT}")


if __name__ == "__main__":
    main()
