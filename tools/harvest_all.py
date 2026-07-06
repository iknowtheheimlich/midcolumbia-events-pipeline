"""Harvest all registered sources and regenerate normalized fixtures.

Attempt_22_Harvest_Infrastructure

Usage:
    python -m tools.harvest_all
    python -m tools.harvest_all --skip-fetch
    python -m tools.harvest_all --source VisitTriCities --source MidColumbiaLibraries
    python -m tools.harvest_all --legacy-input path/to/unified_events.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.harvesters import HarvestOptions, HarvestResult, harvest_adapter
from adapters.registry import AVAILABLE_ADAPTERS, AdapterInfo
from src.pipeline import SourceBatch, run_pipeline
from adapters.algolia.fixtures import load_json_fixture


LINE = "=" * 64


def main() -> None:
    args = parse_args()
    adapters = select_adapters(args.source)
    options = HarvestOptions(
        fetch=not args.skip_fetch,
        regenerate=not args.skip_normalized,
        months=args.months,
        legacy_input=args.legacy_input,
    )

    print(LINE)
    print(" Attempt_22 Harvest Infrastructure")
    print(LINE)

    results: list[HarvestResult] = []
    for adapter in adapters:
        print(f"Harvesting {adapter.source_name}...")
        result = harvest_adapter(adapter, options)
        results.append(result)
        raw_count = "n/a" if result.raw_count is None else str(result.raw_count)
        raw_path = "existing fixture" if result.raw_fixture_path is None else str(result.raw_fixture_path)
        print(f"  raw        {raw_count:>5}  {raw_path}")
        print(f"  normalized {result.normalized_count:>5}  {result.normalized_fixture_path}")

    if not args.skip_pipeline_smoke:
        smoke_pipeline()

    print(LINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest all registered Mid-Columbia event sources")
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(AVAILABLE_ADAPTERS),
        help="Harvest only this source. May be provided multiple times.",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Do not touch the network; regenerate normalized fixtures from saved raw fixtures.",
    )
    parser.add_argument(
        "--skip-normalized",
        action="store_true",
        help="Fetch raw fixtures only; do not rewrite normalized fixtures.",
    )
    parser.add_argument(
        "--skip-pipeline-smoke",
        action="store_true",
        help="Skip the final run_pipeline smoke check.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=2,
        help="Number of months to harvest for monthly-calendar sources.",
    )
    parser.add_argument(
        "--legacy-input",
        type=Path,
        help="Optional legacy unified_events.csv input for LegacyUnifiedCSV regeneration.",
    )
    return parser.parse_args()


def select_adapters(source_names: list[str] | None) -> list[AdapterInfo]:
    """Return selected adapters in stable source-name order."""
    selected = set(source_names or AVAILABLE_ADAPTERS)
    return [AVAILABLE_ADAPTERS[name] for name in sorted(selected)]


def smoke_pipeline() -> None:
    """Run the harvested normalized fixtures through the existing pipeline spine."""
    batches: list[SourceBatch] = []
    for adapter in sorted(AVAILABLE_ADAPTERS.values(), key=lambda item: item.source_name):
        events = load_json_fixture(adapter.fixture_path)
        if not isinstance(events, list):
            raise TypeError(f"fixture must be a list: {adapter.fixture_path}")
        batches.append(SourceBatch(source_name=adapter.source_name, events=events))

    result = run_pipeline(batches, deduplicate=True)
    print()
    print("Pipeline smoke")
    print("--------------")
    print(f"{'Input':<22} {len(result.all_events):>4}")
    print(f"{'Publisher':<22} {len(result.publisher_ready_events):>4}")
    print(f"{'Deduplicated':<22} {len(result.deduplicated_publisher_ready_events):>4}")
    print(f"{'Duplicate Groups':<22} {len(result.duplicate_groups):>4}")
    print(f"{'Series Review':<22} {len(result.recurrence_review_events):>4}")


if __name__ == "__main__":
    main()
