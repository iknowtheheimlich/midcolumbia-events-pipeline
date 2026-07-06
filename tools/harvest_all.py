"""One-command raw harvest, normalized fixture regeneration, and pipeline smoke.

Attempt_22_Harvest_Infrastructure

Usage:
    python -m tools.harvest_all
    python -m tools.harvest_all --skip-fetch
    python -m tools.harvest_all --source VisitTriCities --source TriCityVibe
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.harvest import HarvestOptions, HarvestResult, harvest_adapter
from adapters.registry import AVAILABLE_ADAPTERS, AdapterInfo
from tools.status import load_registered_batches
from src.pipeline import run_pipeline


LINE = "=" * 64


def main() -> None:
    """Run the full harvest infrastructure command."""
    args = parse_args()
    adapters = selected_adapters(args.source)
    options = HarvestOptions(
        fetch_raw=not args.skip_fetch,
        regenerate_normalized=not args.skip_normalized,
        months=args.months,
        legacy_input=args.legacy_input,
    )

    print(LINE)
    print(" Attempt_22 Harvest Infrastructure")
    print(LINE)
    print()

    results: list[HarvestResult] = []
    for adapter in adapters:
        result = harvest_adapter(adapter, options)
        results.append(result)
        print_harvest_result(result)

    if not args.skip_pipeline_smoke:
        print_pipeline_smoke()

    print(LINE)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Harvest all registered Mid-Columbia event sources")
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(AVAILABLE_ADAPTERS),
        help="Harvest only this source. May be passed more than once.",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Do not use the network; regenerate normalized fixtures from saved raw fixtures.",
    )
    parser.add_argument(
        "--skip-normalized",
        action="store_true",
        help="Fetch raw fixtures only; do not rewrite normalized fixtures.",
    )
    parser.add_argument(
        "--skip-pipeline-smoke",
        action="store_true",
        help="Skip final pipeline smoke check.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=2,
        help="Number of current/future months to fetch for monthly calendar sources.",
    )
    parser.add_argument(
        "--legacy-input",
        type=Path,
        help="Optional unified_events.csv path for regenerating the LegacyUnifiedCSV bridge fixture.",
    )
    return parser.parse_args()


def selected_adapters(source_names: list[str] | None) -> list[AdapterInfo]:
    """Return selected registry adapters in stable order."""
    selected = set(source_names or AVAILABLE_ADAPTERS)
    return [AVAILABLE_ADAPTERS[name] for name in sorted(selected)]


def print_harvest_result(result: HarvestResult) -> None:
    """Print one compact source harvest summary."""
    raw_count = "n/a" if result.raw_count is None else str(result.raw_count)
    raw_path = "existing normalized bridge" if result.raw_fixture_path is None else str(result.raw_fixture_path)
    mode = "reused existing normalized fixture" if result.reused_normalized else "regenerated normalized fixture"
    print(f"{result.source_name}")
    print(f"  raw        {raw_count:>5}  {raw_path}")
    print(f"  normalized {result.normalized_count:>5}  {result.normalized_fixture_path}")
    print(f"  mode              {mode}")
    print()


def print_pipeline_smoke() -> None:
    """Run existing pipeline spine against registered normalized fixtures."""
    batches = load_registered_batches()
    result = run_pipeline(batches, deduplicate=True)

    print("Pipeline smoke")
    print("--------------")
    print(f"{'Input':<22} {len(result.all_events):>4}")
    print(f"{'Publisher':<22} {len(result.publisher_ready_events):>4}")
    print(f"{'Deduplicated':<22} {len(result.deduplicated_publisher_ready_events):>4}")
    print(f"{'Duplicate Groups':<22} {len(result.duplicate_groups):>4}")
    print(f"{'Series Review':<22} {len(result.recurrence_review_events):>4}")
    print(f"{'Low Quality Skips':<22} {result.skipped_low_quality_dedupe:>4}")
    print()


if __name__ == "__main__":
    main()
