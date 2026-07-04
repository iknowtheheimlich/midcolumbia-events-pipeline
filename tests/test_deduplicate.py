from __future__ import annotations

from src.deduplicate import deduplicate_events


def test_exact_duplicate_events_merge_and_preserve_sources() -> None:
    events = [
        {
            "title": "Downtown Farmers Market",
            "event_kind": "single",
            "start_date": "2026-07-04",
            "start_time": "09:00",
            "city": "Walla Walla",
            "venue_id": "ChIJYAUoJisQMFQRXYT2W1xW88M",
            "venue": "Prosser Farmers' Market",
            "source": "AllEvents",
            "url": "https://example.com/one",
        },
        {
            "title": "Downtown Farmers Market",
            "event_kind": "single",
            "start_date": "2026-07-04",
            "start_time": "09:00",
            "city": "Walla Walla",
            "venue_id": "ChIJYAUoJisQMFQRXYT2W1xW88M",
            "venue": "Prosser Farmers' Market",
            "source": "VisitTriCities",
            "url": "https://example.com/two",
        },
    ]

    result = deduplicate_events(events)

    assert len(result.events) == 1
    assert len(result.duplicate_groups) == 1
    assert result.events[0]["duplicate_count"] == 2
    assert result.events[0]["sources"] == ["AllEvents", "VisitTriCities"]
    assert result.events[0]["source_urls"] == ["https://example.com/one", "https://example.com/two"]


def test_same_title_different_dates_do_not_merge() -> None:
    events = [
        {
            "title": "Story Time",
            "event_kind": "single",
            "start_date": "2026-07-01",
            "start_time": "10:00",
            "city": "Richland",
            "venue": "Story Circle",
        },
        {
            "title": "Story Time",
            "event_kind": "single",
            "start_date": "2026-07-08",
            "start_time": "10:00",
            "city": "Richland",
            "venue": "Story Circle",
        },
    ]

    result = deduplicate_events(events)

    assert len(result.events) == 2
    assert len(result.duplicate_groups) == 0


def test_low_quality_keys_pass_through_without_merging() -> None:
    events = [
        {"title": "Sparse Event", "start_date": "2026-07-01"},
        {"title": "Sparse Event", "start_date": "2026-07-01"},
    ]

    result = deduplicate_events(events)

    assert len(result.events) == 2
    assert len(result.duplicate_groups) == 0
    assert result.skipped_low_quality == 2
