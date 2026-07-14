from datetime import datetime, timezone
import json
from pathlib import Path

from adapters.harvest import HarvestResult
from src.harvest_health import HarvestHealthReport, SourceHarvestHealth
from src.harvest_telemetry import append_harvest_telemetry, build_harvest_telemetry_records


def _result(*, error: str | None = None, reused: bool = False) -> HarvestResult:
    return HarvestResult(
        source_name="AllEvents",
        raw_fixture_path=None,
        raw_output_path=None,
        normalized_fixture_path=Path("fixtures/allevents.json"),
        raw_count=1,
        normalized_events=[{"title": "Event"}],
        reused_normalized=reused,
        error=error,
    )


def test_build_harvest_telemetry_records_uses_health_classification() -> None:
    result = _result(error="HTTP Error 403")
    health = HarvestHealthReport(
        (
            SourceHarvestHealth(
                source_name="AllEvents",
                status="PARTIAL",
                required=True,
                event_count=1,
                reason=result.error,
            ),
        )
    )

    records = build_harvest_telemetry_records(
        health,
        [result],
        {"AllEvents": 812},
        timestamp=datetime(2026, 7, 13, 23, 0, tzinfo=timezone.utc),
    )

    assert records == [
        {
            "timestamp": "2026-07-13T23:00:00Z",
            "source": "AllEvents",
            "status": "PARTIAL",
            "required": True,
            "events": 1,
            "duration_ms": 812,
            "reused_fixture": False,
            "error": "HTTP Error 403",
        }
    ]


def test_append_harvest_telemetry_preserves_existing_history(tmp_path: Path) -> None:
    path = tmp_path / "telemetry" / "history.jsonl"
    append_harvest_telemetry([{"source": "First", "events": 1}], path)
    append_harvest_telemetry([{"source": "Second", "events": 2}], path)

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert rows == [
        {"events": 1, "source": "First"},
        {"events": 2, "source": "Second"},
    ]
