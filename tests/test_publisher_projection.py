from __future__ import annotations

import pytest

from src.publisher_projection import PublisherEvent, project_event, project_events


def enriched_event() -> dict[str, object]:
    return {
        "title": "Summer Science Night",
        "start_date": "2026-07-17",
        "end_date": "2026-07-17",
        "start_time": "18:00",
        "end_time": "20:00",
        "venue": "Richland Public Library",
        "venue_detail": "Doris Roberts Gallery",
        "venue_id": "ChIJ-example",
        "venue_type": "Library",
        "parent_venue": "Richland Public Library",
        "organization": "Friends of the Richland Library",
        "city": "Richland",
        "state": "WA",
        "geo_scope": "LOCAL",
        "geo_region": "TRI_CITIES",
        "location_type": "VENUE",
        "content_classification": "EVENT",
        "source": "RichlandLibrary",
        "source_event_id": "12345",
        "url": "https://example.org/events/12345",
        "external_url": "https://www.eventbrite.com/e/summer-science-night-tickets-123456789012",
        "category": "Science",
        "description": "Hands-on science for the community.",
        "duplicate_sources": ["RichlandLibrary", "VisitTriCities", "RichlandLibrary"],
    }


def test_project_event_preserves_enriched_publisher_fields() -> None:
    projected = project_event(enriched_event())

    assert isinstance(projected, PublisherEvent)
    assert projected.title == "Summer Science Night"
    assert projected.venue == "Richland Public Library"
    assert projected.parent_venue == "Richland Public Library"
    assert projected.venue_detail == "Doris Roberts Gallery"
    assert projected.venue_type == "Library"
    assert projected.organization == "Friends of the Richland Library"
    assert projected.geographic_scope == "LOCAL"
    assert projected.region == "TRI_CITIES"
    assert projected.content_classification == "EVENT"
    assert projected.eventbrite_event_id == "123456789012"
    assert projected.duplicate_sources == ("RichlandLibrary", "VisitTriCities")


def test_project_event_accepts_legacy_event_without_enrichment() -> None:
    projected = project_event(
        {
            "title": "Legacy Event",
            "venue": "Somewhere",
            "city": "Kennewick",
            "start_date": "2026-07-18",
            "url": "https://example.org/legacy",
            "source": "LegacyUnifiedCSV",
        }
    )

    assert projected.geographic_scope is None
    assert projected.region is None
    assert projected.venue_type is None
    assert projected.organization is None
    assert projected.eventbrite_url is None
    assert projected.duplicate_sources == ()


def test_project_event_preserves_missing_city_for_editorial_review() -> None:
    event = enriched_event()
    event["city"] = ""

    projected = project_event(event)

    assert projected.city is None


def test_project_events_preserves_input_order() -> None:
    first = enriched_event()
    second = {**enriched_event(), "title": "Second Event"}

    projected = project_events([first, second])

    assert [event.title for event in projected] == ["Summer Science Night", "Second Event"]


def test_projection_dict_is_json_serializable_shape() -> None:
    payload = project_event(enriched_event()).to_dict()

    assert payload["duplicate_sources"] == ["RichlandLibrary", "VisitTriCities"]
    assert payload["eventbrite_event_id"] == "123456789012"


@pytest.mark.parametrize("field", ["title", "venue", "start_date", "url", "source"])
def test_missing_required_field_fails_loudly(field: str) -> None:
    event = enriched_event()
    event[field] = ""

    with pytest.raises(ValueError, match=field):
        project_event(event)
