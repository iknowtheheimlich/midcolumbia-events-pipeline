from pathlib import Path

from adapters.harvest import HarvestResult
from adapters.registry import AdapterInfo
from src.harvest_health import assess_harvest_health, degraded_artifact_path


def adapter(name="VisitTriCities", status="active"):
    return AdapterInfo(
        source_name=name,
        adapter_package="adapters.test",
        status=status,
        fixture_path=Path("fixture.json"),
        raw_fixture_path=Path("raw.json"),
        enabled=True,
        priority=100,
    )


def result(name="VisitTriCities", *, events=None, reused=False, error=None):
    return HarvestResult(
        source_name=name,
        raw_fixture_path=Path("raw.json"),
        raw_output_path=None,
        normalized_fixture_path=Path("fixture.json"),
        raw_count=None,
        normalized_events=list(events or []),
        reused_normalized=reused,
        error=error,
    )


def test_clean_active_fetch_is_healthy() -> None:
    report = assess_harvest_health([adapter()], [result(events=[{"title": "A"}])])
    assert report.status == "HEALTHY"
    assert report.sources[0].status == "LIVE"


def test_error_with_fixture_fallback_is_partial_and_degraded() -> None:
    report = assess_harvest_health(
        [adapter()],
        [result(events=[{"title": "cached"}], reused=True, error="DNS failed")],
    )
    assert report.status == "DEGRADED"
    assert report.sources[0].status == "PARTIAL"
    assert report.failed_required_sources[0].source_name == "VisitTriCities"


def test_migration_bridge_is_optional() -> None:
    report = assess_harvest_health(
        [adapter("LegacyUnifiedCSV", status="migration_bridge")],
        [result("LegacyUnifiedCSV", events=[{"title": "legacy"}], reused=True)],
    )
    assert report.status == "HEALTHY"
    assert report.sources[0].status == "OPTIONAL"


def test_degraded_artifact_path_preserves_filename() -> None:
    assert degraded_artifact_path(Path("artifacts/reddit/Main_Events_Post.txt")) == Path(
        "artifacts/degraded/Main_Events_Post.txt"
    )
