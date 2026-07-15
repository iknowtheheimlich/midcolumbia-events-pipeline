from src.plaintext_report import PlaintextReport
from src.review_backlog_throughput import BacklogThroughput, render_throughput_report
from src.review_capacity_planning import ReviewCapacityPlan, render_capacity_report
from src.review_sla import ReviewSLAStats, render_review_sla_report


def test_builder_renders_title_lines_and_final_newline() -> None:
    report = PlaintextReport("Title").line("One").line("Two").render()
    assert report == "Title\n=====\n\nOne\nTwo\n"


def test_builder_inserts_one_blank_before_section() -> None:
    report = PlaintextReport("Title").line("One").section("DETAILS").line("None").render()
    assert report == "Title\n=====\n\nOne\n\nDETAILS\n-------\nNone\n"


def test_throughput_report_output_is_unchanged() -> None:
    metrics = BacklogThroughput(2, 3, 2, 1, 1, 1, 1, 1 / 3, "growing")
    assert render_throughput_report(metrics) == (
        "Attempt 88 Review Backlog Throughput\n"
        "====================================\n\n"
        "Prior active: 2\n"
        "Current active: 3\n"
        "Opened: 2\n"
        "Carried: 1\n"
        "Resolved: 1\n"
        "Net change: +1\n"
        "Stale: 1 (33.3%)\n"
        "Trend: growing\n"
    )


def test_capacity_report_output_is_unchanged() -> None:
    plan = ReviewCapacityPlan(4, 1.5, 2.5, 1.0, 4.0, "recovering")
    assert render_capacity_report(plan) == (
        "Attempt 90 Review Capacity Planning\n"
        "===================================\n\n"
        "Active backlog: 4\n"
        "Average opened/week: 1.5\n"
        "Average resolved/week: 2.5\n"
        "Net clearance/week: +1.0\n"
        "Estimated time to clear: 4.0 weeks\n"
        "Status: recovering\n"
    )


def test_sla_report_output_is_unchanged() -> None:
    backlog = {
        "1|Sports": {
            "title": "Example",
            "category": "Sports",
            "sla_status": "overdue",
            "age_days": 15,
            "appearances": 4,
            "confidence": 0.4,
        }
    }
    stats = ReviewSLAStats(active=1, due_soon=0, overdue=1, oldest_days=15)
    assert render_review_sla_report(backlog, stats) == (
        "Attempt 89 Review SLA\n"
        "=====================\n\n"
        "Active: 1\n"
        "Due soon: 0\n"
        "Overdue: 1\n"
        "Oldest age: 15 days\n\n"
        "OVERDUE / DUE SOON\n"
        "------------------\n"
        "Example | Sports | overdue | age=15d | appearances=4\n"
    )
