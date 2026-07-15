from pathlib import Path

from src.review_backlog_throughput import (
    analyze_backlog_throughput,
    append_throughput,
    render_throughput_report,
)


def row(status: str = "new") -> dict:
    return {"status": status}


def test_growing_backlog_metrics() -> None:
    metrics = analyze_backlog_throughput({"a": row()}, {"a": row(), "b": row("stale")})
    assert metrics.opened == 1
    assert metrics.carried == 1
    assert metrics.resolved == 0
    assert metrics.net_change == 1
    assert metrics.stale_share == 0.5
    assert metrics.trend == "growing"


def test_shrinking_backlog_metrics() -> None:
    metrics = analyze_backlog_throughput({"a": row(), "b": row()}, {"b": row()})
    assert metrics.opened == 0
    assert metrics.carried == 1
    assert metrics.resolved == 1
    assert metrics.net_change == -1
    assert metrics.trend == "shrinking"


def test_flat_backlog_can_still_turn_over() -> None:
    metrics = analyze_backlog_throughput({"a": row()}, {"b": row()})
    assert metrics.opened == 1
    assert metrics.resolved == 1
    assert metrics.net_change == 0
    assert metrics.trend == "flat"


def test_append_and_render(tmp_path: Path) -> None:
    metrics = analyze_backlog_throughput({}, {"a": row("stale")})
    path = tmp_path / "throughput.jsonl"
    append_throughput(path, "2026-07-15", metrics)
    text = path.read_text(encoding="utf-8")
    assert '"run_date": "2026-07-15"' in text
    assert "Trend: growing" in render_throughput_report(metrics)
