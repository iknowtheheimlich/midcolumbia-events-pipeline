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


def test_semantic_cross_source_duplicate_merges_title_and_venue_aliases() -> None:
    common = {"event_kind":"single", "start_date":"2026-08-18", "start_time":"18:00", "city":"Kennewick"}
    result = deduplicate_events([
        {**common, "title":"Craft Collective: Stenciled Book Edges", "venue":"Kennewick Branch - Mid-Columbia Libraries", "source":"AllEvents"},
        {**common, "title":"The Craft Collective: Stenciled Book Edges", "venue":"Kennewick Mid-Columbia Library", "source":"MidColumbiaLibraries"},
    ])
    assert len(result.events) == 1
    assert result.duplicate_groups[0]["dedupe_key"] == "semantic_occurrence"


def test_same_artist_time_different_city_does_not_semantically_merge() -> None:
    result = deduplicate_events([
        {"title":"Jamie Buckley", "start_date":"2026-08-22", "start_time":"20:00", "city":"Kennewick", "venue":"One", "source":"A"},
        {"title":"Jamie Buckley", "start_date":"2026-08-22", "start_time":"20:00", "city":"Pasco", "venue":"Two", "source":"B"},
    ])
    assert len(result.events) == 2


def test_semantic_duplicate_uses_cross_source_venue_description_support() -> None:
    common = {"start_date":"2026-08-18", "start_time":"11:00", "city":"Kennewick"}
    result = deduplicate_events([
        {**common, "title":"Barnes & Noble Presents Children's Story-time!", "venue":"Columbia Center Mall", "description":"Story time at the Barnes & Noble in Kennewick", "source":"AllEvents"},
        {**common, "title":"Children's Story-time!", "venue":"Barnes & Noble", "description":"", "source":"NotionWeekly"},
    ])
    assert len(result.events) == 1


def test_same_venue_time_generic_music_titles_preserve_distinct_artists() -> None:
    common = {"start_date":"2026-08-21", "start_time":"18:00", "city":"Kennewick", "venue":"The Peacock"}
    result = deduplicate_events([
        {**common, "title":"Live Music with Common Thread Duo at The Peacock", "source":"TriCityVibe"},
        {**common, "title":"Live Music with Dane Pollard at The Peacock!", "source":"AllEvents"},
    ])
    assert len(result.events) == 2


def test_merge_uses_venue_corroborated_by_cross_source_content() -> None:
    common = {"start_date":"2026-08-19", "start_time":"15:00", "city":"Prosser"}
    result = deduplicate_events([
        {**common, "title":"Wine Down Wednesday @ Evergreen Family Wines", "venue":"Milbrandt Family Wines - Prosser", "description":"Join us at Evergreen Family Wines", "url":"https://evergreenfamilywines.com/events/", "source":"VisitTriCities"},
        {**common, "title":"Wine Down Wednesday", "venue":"Evergreen Family Wines", "url":"https://evergreenfamilywines.com/", "source":"NotionWeekly"},
    ])
    assert result.events[0]["venue"] == "Evergreen Family Wines"
