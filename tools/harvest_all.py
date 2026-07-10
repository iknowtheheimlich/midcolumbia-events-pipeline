"""One-command raw harvest, normalized output generation, and pipeline smoke.

Attempt_22_Harvest_Infrastructure

Usage:
    python -m tools.harvest_all
    python -m tools.harvest_all --skip-fetch
    python -m tools.harvest_all --write-normalized-fixtures
    python -m tools.harvest_all --write-raw-fixtures
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.algolia.fixtures import save_json_fixture
from adapters.harvest import HarvestOptions, HarvestResult, harvest_adapter
from adapters.registry import AVAILABLE_ADAPTERS, AdapterInfo
from src.pipeline import SourceBatch, run_pipeline


LINE = "=" * 64
GENERATED_ROOT = Path("generated/harvest")


def main() -> None:
    """Run the full harvest infrastructure command."""
    args = parse_args()
    adapters = selected_adapters(args.source)
    options = HarvestOptions(
        fetch_raw=not args.skip_fetch,
        write_raw=args.write_raw_fixtures,
        write_normalized=args.write_normalized_fixtures,
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
        save_generated_normalized(result)
        print_harvest_result(
            result,
            requested_normalized_write=args.write_normalized_fixtures,
            requested_raw_write=args.write_raw_fixtures,
        )

    if not args.skip_pipeline_smoke:
        print_pipeline_smoke(results)

    warned = [result for result in results if result.error]
    if warned:
        print("Harvest warnings")
        print("----------------")
        for result in warned:
            print(f"{result.source_name}: {result.error}")
        print()

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
        help="Do not use the network; regenerate from saved raw fixtures when available.",
    )
    parser.add_argument(
        "--write-normalized-fixtures",
        action="store_true",
        help="Rewrite tracked normalized fixtures. Use only when intentionally refreshing golden fixtures.",
    )
    parser.add_argument(
        "--write-raw-fixtures",
        action="store_true",
        help="Rewrite tracked raw fixtures. Use only when intentionally refreshing golden fixtures.",
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


def generated_output_path(result: HarvestResult) -> Path:
    """Return generated normalized output path for one source."""
    return GENERATED_ROOT / result.source_name / "normalized_events.json"


def save_generated_normalized(result: HarvestResult) -> None:
    """Write generated live normalized output outside tracked fixture paths."""
    save_json_fixture(generated_output_path(result), result.normalized_events)


def print_harvest_result(
    result: HarvestResult,
    *,
    requested_normalized_write: bool,
    requested_raw_write: bool,
) -> None:
    """Print one compact source harvest summary."""
    raw_count = "n/a" if result.raw_count is None else str(result.raw_count)
    raw_path = "not applicable" if result.raw_output_path is None else str(result.raw_output_path)
    raw_updated = requested_raw_write and result.raw_output_path is not None and result.error is None
    normalized_updated = requested_normalized_write and not result.reused_normalized and result.error is None
    mode = "reused existing normalized fixture" if result.reused_normalized else "generated normalized output"

    print(f"{result.source_name}")
    print(f"  raw        {raw_count:>5}  {raw_path}")
    print(f"  raw fixture       {'updated' if raw_updated else 'preserved'}")
    print(f"  normalized {result.normalized_count:>5}  {generated_output_path(result)}")
    print(f"  fixture           {'updated' if normalized_updated else 'preserved'}  {result.normalized_fixture_path}")
    print(f"  mode              {mode}")
    if result.error:
        print("  warning           preserved normalized fixture after harvest error")
    print()


def print_pipeline_smoke(results: list[HarvestResult]) -> None:
    """Run existing pipeline spine against in-memory harvest results."""
    batches = [SourceBatch(source_name=result.source_name, events=result.normalized_events) for result in results]
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
