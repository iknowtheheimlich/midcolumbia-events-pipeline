from src.review_capacity_planning import analyze_review_capacity, render_capacity_report


def test_recovering_backlog_has_clearance_eta() -> None:
    history = [
        {"opened": 2, "resolved": 5},
        {"opened": 1, "resolved": 4},
    ]
    plan = analyze_review_capacity(history, active_backlog=12)
    assert plan.status == "recovering"
    assert plan.net_clearance == 3.0
    assert plan.weeks_to_clear == 4.0


def test_over_capacity_has_no_clearance_eta() -> None:
    plan = analyze_review_capacity([{"opened": 5, "resolved": 2}], active_backlog=10)
    assert plan.status == "over_capacity"
    assert plan.weeks_to_clear is None


def test_empty_backlog_is_clear() -> None:
    plan = analyze_review_capacity([], active_backlog=0)
    assert plan.status == "clear"
    assert plan.weeks_to_clear == 0.0


def test_lookback_uses_most_recent_rows() -> None:
    history = [
        {"opened": 100, "resolved": 0},
        {"opened": 1, "resolved": 3},
        {"opened": 1, "resolved": 3},
    ]
    plan = analyze_review_capacity(history, active_backlog=8, lookback=2)
    assert plan.net_clearance == 2.0
    assert plan.weeks_to_clear == 4.0


def test_report_explains_nonclearing_backlog() -> None:
    plan = analyze_review_capacity([{"opened": 2, "resolved": 2}], active_backlog=5)
    report = render_capacity_report(plan)
    assert "not currently clearing" in report
    assert "Status: balanced" in report
