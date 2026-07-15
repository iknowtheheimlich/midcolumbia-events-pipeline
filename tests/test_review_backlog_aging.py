from pathlib import Path

from src.review_backlog_aging import load_backlog, reconcile_backlog, write_backlog


def event(event_id: str = "1", category: str = "Sports", confidence: float = 0.4, review: bool = True) -> dict:
    return {
        "event_id": event_id,
        "title": "Example",
        "category": category,
        "category_confidence": confidence,
        "category_needs_review": review,
    }


def test_new_review_decision_enters_backlog() -> None:
    backlog, stats = reconcile_backlog([event()], {}, seen_on="2026-07-15")
    row = backlog["1|Sports"]
    assert row["status"] == "new"
    assert row["appearances"] == 1
    assert stats.new == 1


def test_repeated_decision_ages_to_stale() -> None:
    first, _ = reconcile_backlog([event()], {}, seen_on="2026-07-01", stale_after=3)
    second, _ = reconcile_backlog([event()], first, seen_on="2026-07-08", stale_after=3)
    third, stats = reconcile_backlog([event()], second, seen_on="2026-07-15", stale_after=3)
    assert third["1|Sports"]["status"] == "stale"
    assert stats.stale == 1


def test_changed_category_is_new_decision_and_old_is_resolved() -> None:
    prior, _ = reconcile_backlog([event(category="Sports")], {}, seen_on="2026-07-01")
    current, stats = reconcile_backlog([event(category="Community Events")], prior, seen_on="2026-07-08")
    assert "1|Sports" not in current
    assert current["1|Community Events"]["status"] == "new"
    assert stats.resolved == 1


def test_nonreviewable_decision_drops_out() -> None:
    prior, _ = reconcile_backlog([event()], {}, seen_on="2026-07-01")
    current, stats = reconcile_backlog([event(review=False)], prior, seen_on="2026-07-08")
    assert current == {}
    assert stats.resolved == 1


def test_backlog_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "backlog.json"
    backlog, _ = reconcile_backlog([event()], {}, seen_on="2026-07-15")
    write_backlog(path, backlog)
    assert load_backlog(path) == backlog
