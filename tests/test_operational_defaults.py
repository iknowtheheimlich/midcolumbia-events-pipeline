import inspect

from src.operational_defaults import (
    CAPACITY_LOOKBACK_RUNS,
    SLA_DUE_AFTER_DAYS,
    SLA_OVERDUE_AFTER_APPEARANCES,
    SLA_OVERDUE_AFTER_DAYS,
    STALE_AFTER_APPEARANCES,
)
from src.review_backlog_aging import reconcile_backlog
from src.review_capacity_planning import analyze_review_capacity
from src.review_sla import apply_review_sla
from tools.finalize_weekly_run import finalize_weekly_run


def default_of(function, name: str):
    return inspect.signature(function).parameters[name].default


def test_library_defaults_share_one_source_of_truth() -> None:
    assert default_of(reconcile_backlog, "stale_after") == STALE_AFTER_APPEARANCES
    assert default_of(apply_review_sla, "due_after_days") == SLA_DUE_AFTER_DAYS
    assert default_of(apply_review_sla, "overdue_after_days") == SLA_OVERDUE_AFTER_DAYS
    assert default_of(apply_review_sla, "overdue_after_appearances") == SLA_OVERDUE_AFTER_APPEARANCES
    assert default_of(analyze_review_capacity, "lookback") == CAPACITY_LOOKBACK_RUNS


def test_weekly_finalizer_uses_shared_defaults() -> None:
    assert default_of(finalize_weekly_run, "stale_after") == STALE_AFTER_APPEARANCES
    assert default_of(finalize_weekly_run, "due_after_days") == SLA_DUE_AFTER_DAYS
    assert default_of(finalize_weekly_run, "overdue_after_days") == SLA_OVERDUE_AFTER_DAYS
    assert default_of(finalize_weekly_run, "overdue_after_appearances") == SLA_OVERDUE_AFTER_APPEARANCES
    assert default_of(finalize_weekly_run, "capacity_lookback") == CAPACITY_LOOKBACK_RUNS


def test_explicit_overrides_still_take_precedence() -> None:
    event = {
        "event_id": "1",
        "title": "One",
        "category": "Sports",
        "category_confidence": 0.4,
        "category_needs_review": True,
    }
    prior = {
        "1|Sports": {
            "event_id": "1",
            "title": "One",
            "category": "Sports",
            "confidence": 0.4,
            "first_seen": "2026-07-01",
            "last_seen": "2026-07-08",
            "appearances": 1,
            "status": "new",
        }
    }
    backlog, _ = reconcile_backlog([event], prior, seen_on="2026-07-15", stale_after=2)
    assert backlog["1|Sports"]["status"] == "stale"

    enriched, stats = apply_review_sla(
        backlog,
        as_of="2026-07-15",
        due_after_days=1,
        overdue_after_days=2,
        overdue_after_appearances=99,
    )
    assert enriched["1|Sports"]["sla_status"] == "overdue"
    assert stats.overdue == 1
