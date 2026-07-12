from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.harvest import HarvestResult
from adapters.registry import AdapterInfo
from src.source_metrics import build_source_metrics, render_source_metrics, write_source_metrics


def adapter(name: str, priority: int) -> AdapterInfo:
    return AdapterInfo(
        source_name=name,
        adapter_package=f"adapters.{name.casefold()}",
        status="active",
        fixture_path=Path(f"fixtures/{name}/events.json"),
        enabled=True,
        priority=priority,
    )


def harvest(name: str, count: int, error: str | None = None) -> HarvestResult:
    return HarvestResult(
        source_name=name,
        raw_fixture_path=None,
        raw_output_path=None,
        normalized_fixture_path=Path(f"fixtures/{name}/events.json"),
        raw_count=count,
        normalized_events=[{"title": str(index)} for index in range(count)],
        error=error,
    )


def editorial(**overrides):
    values = {
        "source": "A",
        "duplicate_sources": (),
        "publication_disposition": "AUTO_PUBLISH",
        "publication_target": "MAIN",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_metrics_credit_all_contributing_sources_and_removed_duplicates() -> None:
    metrics = build_source_metrics(
        [adapter("A", 100), adapter("B", 50)],
        [harvest("A", 3), harvest("B", 2)],
        content_rejected_events=[{"source": "B"}],
        duplicate_groups=[
            {
                "source_events": [
                    {"source": "A"},
                    {"source": "B"},
                ]
            }
        ],
        editorial_events=[
            editorial(source="A", duplicate_sources=("A", "B")),
            editorial(
                source="B",
                publication_disposition="REVIEW",
                publication_target="REVIEW",
            ),
        ],
    )

    by_name = {item.source_name: item for item in metrics}
    assert by_name["A"].harvested == 3
    assert by_name["A"].main_published == 1
    assert by_name["A"].duplicates_removed == 0
    assert by_name["B"].harvested == 2
    assert by_name["B"].content_rejected == 1
    assert by_name["B"].duplicates_removed == 1
    assert by_name["B"].main_published == 1
    assert by_name["B"].review == 1


def test_metrics_render_in_priority_order() -> None:
    metrics = build_source_metrics(
        [adapter("Low", 1), adapter("High", 100)],
        [harvest("Low", 1), harvest("High", 2, error="fallback used")],
    )

    report = render_source_metrics(metrics)

    assert report.index("High") < report.index("Low")
    assert "Harvest warning: fallback used" in report


def test_metrics_artifact_cannot_be_written_into_fixtures(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="separate from fixtures"):
        write_source_metrics([], tmp_path / "fixtures" / "metrics.txt")
