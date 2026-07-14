from datetime import date

from src.completeness_audit import build_completeness_rows, render_completeness_audit
from src.deduplicate import merge_group
from src.event_completeness import enrich_event_completeness, score_event_completeness, summarize_completeness


def _base_event(**updates):
    event = {
        "title": "Community Concert",
        "start_date": "2026-07-14",
        "start_time": "18:00",
        "venue": "Howard Amon Park",
        "city": "Richland",
        "url": "https://example.com/event",
        "source": "AllEvents",
    }
    event.update(updates)
    return event


def test_complete_event_scores_higher_than_sparse_event():
    sparse = score_event_completeness(_base_event())
    rich = score_event_completeness(
        _base_event(
            description="Music in the park.",
            organization="City of Richland",
            address="500 Amon Park Dr",
            category="Music/Comedy",
            image_url="https://example.com/image.jpg",
            cost="Free",
            schedule_items=[{"time": "6 PM", "label": "Doors"}],
        )
    )
    assert rich["score"] > sparse["score"]
    assert rich["percent"] > sparse["percent"]


def test_alternative_venue_and_url_fields_satisfy_completeness():
    details = score_event_completeness(
        _base_event(venue="", venue_id="venue-1", url="", external_url="https://example.com/external")
    )
    assert "venue" in details["present_fields"]
    assert "url" in details["present_fields"]


def test_enrichment_attaches_score_missing_fields_and_intelligence():
    event = enrich_event_completeness(_base_event())
    assert 0 < event["completeness_score"] < 1
    assert event["completeness_percent"] == round(event["completeness_score"] * 100)
    assert "description" in event["completeness_missing"]
    assert event["intelligence"]["completeness"]["reason"] == "weighted_field_presence"


def test_summary_reports_average_and_common_missing_fields():
    summary = summarize_completeness([_base_event(), _base_event(description="Present")])
    assert summary["event_count"] == 2
    assert summary["average_percent"] > 0
    assert summary["missing_counts"]["image_url"] == 2
    assert summary["missing_counts"]["description"] == 1


def test_exact_duplicate_merge_chooses_more_complete_record_over_higher_priority_source():
    sparse_high_priority = enrich_event_completeness(
        _base_event(source="VisitTriCities")
    )
    rich_lower_priority = enrich_event_completeness(
        _base_event(
            source="AllEvents",
            description="Full description",
            organization="Organizer",
            address="500 Amon Park Dr",
            category="Music/Comedy",
            image_url="https://example.com/image.jpg",
            cost="Free",
        )
    )
    merged = merge_group([sparse_high_priority, rich_lower_priority])
    assert merged["source"] == "AllEvents"
    assert merged["description"] == "Full description"
    assert merged["duplicate_count"] == 2


def test_completeness_audit_only_lists_events_below_threshold():
    sparse = _base_event()
    rich = _base_event(
        title="Rich Event",
        description="Description",
        organization="Organizer",
        address="Address",
        category="Music/Comedy",
        image_url="image",
        cost="Free",
        schedule_items=[{"time": "6 PM", "label": "Doors"}],
        registration_info="Register online",
        end_time="21:00",
    )
    rows = build_completeness_rows([sparse, rich], week_start=date(2026, 7, 13), threshold=80)
    assert [row["title"] for row in rows] == ["Community Concert"]
    assert "description" in rows[0]["missing_fields"]


def test_completeness_audit_renders_summary_and_missing_fields():
    text = render_completeness_audit(
        [_base_event()],
        week_start=date(2026, 7, 13),
        threshold=90,
    )
    assert "Weekly events measured: 1" in text
    assert "Average completeness:" in text
    assert "Low-completeness events:" in text
    assert "Missing:" in text
