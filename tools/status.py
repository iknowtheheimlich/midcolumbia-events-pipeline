"""Print a compact status report for the Mid-Columbia Events Pipeline."""

from __future__ import annotations

from pathlib import Path

from adapters.algolia.fixtures import load_json_fixture
from adapters.registry import AVAILABLE_ADAPTERS
from src.pipeline import SourceBatch, run_pipeline


LINE = "=" * 49


def main() -> None:
    batches = load_registered_batches()
    result = run_pipeline(batches, deduplicate=True)

    print(LINE)
    print(" Mid-Columbia Event Pipeline")
    print(LINE)
    print()
    print("Adapters")
    print("--------")
    for name, adapter in sorted(AVAILABLE_ADAPTERS.items()):
        print(f"{name:<22} {adapter.status.upper()}")

    print()
    print("Fixtures")
    print("--------")
    for batch in batches:
        print(f"{batch.source_name:<22} {len(batch.events):>4} events")

    print()
    print("Latest Pipeline")
    print("---------------")
    print(f"{'Input':<22} {len(result.all_events):>4}")
    print(f"{'Publisher':<22} {len(result.publisher_ready_events):>4}")
    print(f"{'Deduplicated':<22} {len(result.deduplicated_publisher_ready_events):>4}")
    print(f"{'Series Review':<22} {len(result.recurrence_review_events):>4}")
    print(f"{'Duplicate Groups':<22} {len(result.duplicate_groups):>4}")
    print(f"{'Low Quality Skips':<22} {result.skipped_low_quality_dedupe:>4}")
    print()
    print(LINE)


def load_registered_batches() -> list[SourceBatch]:
    batches: list[SourceBatch] = []
    for adapter in sorted(AVAILABLE_ADAPTERS.values(), key=lambda item: item.source_name):
        events = load_fixture(adapter.fixture_path)
        batches.append(SourceBatch(source_name=adapter.source_name, events=events))
    return batches


def load_fixture(path: Path) -> list[dict]:
    events = load_json_fixture(path)
    if not isinstance(events, list):
        raise TypeError(f"fixture must be a list: {path}")
    return events


if __name__ == "__main__":
    main()
