from dataclasses import dataclass
import json
from pathlib import Path

from src.mission_run_summary import write_production_mission_control


@dataclass(frozen=True)
class Health:
    source_name: str
    status: str
    event_count: int
    reason: str | None = None


def test_live_production_state_writes_latest_and_archive(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    corpus = Path("generated/corpus/summary.json")
    corpus.parent.mkdir(parents=True)
    corpus.write_text(json.dumps({"historical_events": 1631, "venues": 373, "hosts": 327}), encoding="utf-8")

    report, outputs = write_production_mission_control(
        week_start="2026-07-13",
        production_status="HEALTHY",
        source_health=[Health("AllEvents", "LIVE", 12), Health("OptionalFeed", "OPTIONAL", 3)],
        source_durations_ms={"AllEvents": 125, "OptionalFeed": 20},
        counts={"main": 8, "community": 4, "review": 0, "rejected": 0},
        artifacts={"main": Path("artifacts/reddit/Main_Events_Post.txt")},
    )

    assert report.ready_to_publish is True
    assert report.knowledge["historical_events"] == 1631
    assert report.sources[0].status == "HEALTHY"
    assert outputs["latest_dashboard"].exists()
    assert outputs["archive_flight_recorder"].exists()


def test_cached_required_source_holds_mission(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    report, _ = write_production_mission_control(
        week_start="2026-07-13",
        production_status="DEGRADED",
        source_health=[Health("AllEvents", "CACHED", 12, "fixture reused")],
        source_durations_ms={},
        counts={"review": 0, "rejected": 0},
        artifacts={},
    )
    assert report.ready_to_publish is False
