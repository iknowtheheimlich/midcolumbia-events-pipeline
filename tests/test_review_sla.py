from pathlib import Path

from src.review_sla import apply_review_sla, render_review_sla_report
from tests.builders import build_backlog, build_event
from tests.history_helpers import finalizer_paths, write_json
from tools.finalize_weekly_run import finalize_weekly_run


def test_due_soon_by_age() -> None:
    enriched, stats = apply_review_sla(
        build_backlog(first_seen="2026-07-08"), as_of="2026-07-15"
    )
    assert enriched["1|Sports"]["sla_status"] == "due_soon"
    assert stats.due_soon == 1


def test_overdue_by_age() -> None:
    enriched, stats = apply_review_sla(
        build_backlog(first_seen="2026-07-01"), as_of="2026-07-15"
    )
    assert enriched["1|Sports"]["sla_status"] == "overdue"
    assert stats.overdue == 1
    assert stats.oldest_days == 14


def test_overdue_by_appearances() -> None:
    enriched, stats = apply_review_sla(
        build_backlog(first_seen="2026-07-14", appearances=4),
        as_of="2026-07-15",
    )
    assert enriched["1|Sports"]["sla_status"] == "overdue"
    assert stats.overdue == 1


def test_report_lists_overdue() -> None:
    enriched, stats = apply_review_sla(build_backlog(), as_of="2026-07-15")
    report = render_review_sla_report(enriched, stats)
    assert "Overdue: 1" in report
    assert "Example | Sports | overdue" in report


def test_finalizer_writes_sla_report(tmp_path: Path) -> None:
    input_path = write_json(tmp_path / "events.json", [build_event()])
    result = finalize_weekly_run(
        input_path,
        **finalizer_paths(tmp_path),
        run_reports=False,
    )
    assert Path(result["review_sla_report"]).exists()
    assert result["review_sla_overdue"] == 0
