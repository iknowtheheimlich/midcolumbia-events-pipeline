from pathlib import Path

from src.classification_review_feedback import (
    analyze_feedback,
    append_feedback,
    build_feedback,
    load_feedback,
    render_feedback_report,
)


def sample_event(**overrides):
    event = {
        "event_id": "evt-1",
        "title": "Paint Your Pet",
        "category": "Community Programs",
        "category_confidence": 0.76,
        "category_reason": "venue_type=library",
        "category_evidence": [{"type": "venue_type", "value": "library"}],
        "venue": "Richland Public Library",
        "organization": "Art YOUR Way",
        "source": "allevents",
    }
    event.update(overrides)
    return event


def test_build_feedback_preserves_classification_observability():
    feedback = build_feedback(sample_event(), "Classes/Workshops", reviewed_at="2026-07-15T18:00:00Z")
    assert feedback.original_category == "Community Programs"
    assert feedback.corrected_category == "Classes/Workshops"
    assert feedback.category_confidence == 0.76
    assert feedback.category_reason == "venue_type=library"
    assert feedback.category_evidence[0]["type"] == "venue_type"


def test_feedback_id_is_deterministic_for_same_review():
    first = build_feedback(sample_event(), "Classes/Workshops", reviewed_at="2026-07-15T18:00:00Z")
    second = build_feedback(sample_event(), "Classes/Workshops", reviewed_at="2026-07-15T18:00:00Z")
    assert first.feedback_id == second.feedback_id


def test_append_feedback_is_idempotent(tmp_path: Path):
    path = tmp_path / "reviews.jsonl"
    feedback = build_feedback(sample_event(), "Classes/Workshops", reviewed_at="2026-07-15T18:00:00Z")
    assert append_feedback(path, feedback) is True
    assert append_feedback(path, feedback) is False
    assert len(load_feedback(path)) == 1


def test_analysis_counts_category_transitions_and_entities():
    rows = [
        build_feedback(sample_event(), "Classes/Workshops", reviewed_at="2026-07-15T18:00:00Z").to_dict(),
        build_feedback(
            sample_event(event_id="evt-2", title="Another Class", category_confidence=0.62),
            "Classes/Workshops",
            reviewed_at="2026-07-15T18:01:00Z",
        ).to_dict(),
    ]
    summary = analyze_feedback(rows)
    assert summary["reviews"] == 2
    assert summary["corrected"] == 2
    assert summary["top_transitions"][0] == ("Community Programs -> Classes/Workshops", 2)
    assert summary["top_venues"][0][0] == "Richland Public Library"
    assert summary["top_organizers"][0][0] == "Art YOUR Way"


def test_analysis_separates_accepted_reviews_from_corrections():
    corrected = build_feedback(sample_event(), "Classes/Workshops", reviewed_at="2026-07-15T18:00:00Z").to_dict()
    accepted = build_feedback(sample_event(event_id="evt-2"), "Community Programs", reviewed_at="2026-07-15T18:01:00Z").to_dict()
    summary = analyze_feedback([corrected, accepted])
    assert summary["accepted_without_change"] == 1
    assert summary["corrected"] == 1
    assert summary["override_rate"] == 0.5


def test_report_renders_empty_ledger_without_failure():
    report = render_feedback_report(analyze_feedback([]))
    assert "Reviews: 0" in report
    assert "Override rate: 0.0%" in report
    assert "TOP CATEGORY TRANSITIONS" in report
