from dataclasses import replace

import pytest

from src.geography import classify_event
from src.publisher_editorial import (
    apply_editorial_rules,
    auto_publish_events,
    community_events,
    main_events,
    rejected_events,
    review_events,
)
from src.publisher_projection import PublisherEvent


def make_event(**overrides):
    base = PublisherEvent(
        title="Community Event",
        start_date="2026-07-18",
        end_date=None,
        start_time="09:30",
        end_time="11:00",
        venue="Richland Public Library",
        parent_venue=None,
        venue_detail=None,
        venue_id="place-1",
        venue_type="Library",
        organization=None,
        city="Richland",
        state="WA",
        geographic_scope="LOCAL",
        region="TRI_CITIES",
        location_type="VENUE",
        content_classification="EVENT",
        content_rejection_reason=None,
        source="RichlandLibrary",
        source_event_id="abc",
        source_url="https://library.example/event",
        source_urls=("https://library.example/event",),
        external_url=None,
        eventbrite_url=None,
        eventbrite_event_id=None,
        category="Community Programs",
        description=None,
        duplicate_sources=(),
        duplicate_count=1,
    )
    return replace(base, **overrides)


def test_library_name_is_standardized():
    result = apply_editorial_rules(make_event())
    assert result.display_venue == "Richland Library"


def test_duplicate_city_suffix_is_removed():
    result = apply_editorial_rules(make_event(venue="The REACH - Richland"))
    assert result.display_venue == "The REACH"


def test_parent_room_is_rendered_with_parent_venue():
    result = apply_editorial_rules(
        make_event(
            venue="Richland Public Library",
            parent_venue="Richland Public Library",
            venue_detail="Doris Roberts Gallery",
        )
    )
    assert result.display_venue == "Doris Roberts Gallery, Richland Library"


def test_duplicate_organization_is_suppressed():
    result = apply_editorial_rules(make_event(organization="Richland Public Library"))
    assert result.display_organization is None


def test_distinct_organization_is_preserved():
    result = apply_editorial_rules(make_event(organization="Friends of the Library"))
    assert result.display_organization == "Friends of the Library"


def test_external_url_is_preferred_over_listing_url():
    result = apply_editorial_rules(
        make_event(
            external_url="https://tickets.example/register",
            eventbrite_url="https://www.eventbrite.com/e/example-1234567890",
        )
    )
    assert result.publication_url == "https://tickets.example/register"


def test_time_is_formatted_using_compact_contract():
    result = apply_editorial_rules(make_event(start_time="09:30", end_time="11:00"))
    assert result.display_time == "9:30-11a"
    assert result.display_start_time == "09:30"


def test_local_community_event_auto_publishes_to_community():
    result = apply_editorial_rules(make_event())
    assert result.publication_disposition == "AUTO_PUBLISH"
    assert result.publication_target == "COMMUNITY"
    assert auto_publish_events([result]) == [result]
    assert community_events([result]) == [result]
    assert main_events([result]) == []


def test_music_event_routes_to_main():
    result = apply_editorial_rules(make_event(category="Music/Comedy"))
    assert result.publication_target == "MAIN"
    assert main_events([result]) == [result]


def test_missing_category_routes_to_review():
    result = apply_editorial_rules(make_event(category=None))
    assert result.publication_disposition == "REVIEW"
    assert result.editorial_reason == "missing_or_unknown_category"


def test_empty_post_presentation_venue_routes_to_explicit_review():
    result = apply_editorial_rules(
        make_event(venue="Richland, Washington", city="Richland", category="Music/Comedy")
    )

    assert result.display_venue == ""
    assert result.publication_disposition == "REVIEW"
    assert result.editorial_reason == "missing_venue"


def test_facebook_share_external_url_falls_back_to_stable_source_with_audit_reason():
    result = apply_editorial_rules(
        make_event(
            title="Sip & Sing",
            source_url="https://www.visittri-cities.com/sip-sing/",
            external_url="https://www.facebook.com/share/1EgaqDHA6R/",
        )
    )

    assert result.publication_url == "https://www.visittri-cities.com/sip-sing/"
    assert result.publication_url_reason == "external_facebook_share_rejected_source_fallback"
    assert result.publication_disposition == "AUTO_PUBLISH"


def test_facebook_share_without_stable_source_routes_to_review():
    result = apply_editorial_rules(
        make_event(
            external_url="https://www.facebook.com/share/1EgaqDHA6R/",
            source_url="https://www.facebook.com/share/source/",
        )
    )

    assert result.publication_disposition == "REVIEW"
    assert result.editorial_reason == "invalid_publication_url"


def test_invalid_authoritative_display_url_cannot_fall_back_to_source():
    result = apply_editorial_rules(
        make_event(
            display_url="https://www.facebook.com/share/venue-record/",
            source_url="https://source.example/stable-event",
        )
    )

    assert result.publication_disposition == "REVIEW"
    assert result.editorial_reason == "invalid_publication_url"
    assert result.publication_url == "https://www.facebook.com/share/venue-record/"


def test_conflicting_occurrence_blocker_survives_editorial_projection():
    details = ({"source": "AllEvents", "reason": "conflicting_occurrence"},)
    result = apply_editorial_rules(
        make_event(
            publication_blocker_reason="conflicting_occurrence",
            publication_blocker_details=details,
        )
    )

    assert result.publication_disposition == "REVIEW"
    assert result.editorial_reason == "conflicting_occurrence"
    assert result.publication_blocker_details == details


def test_regional_event_routes_to_review():
    result = apply_editorial_rules(make_event(geographic_scope="REGIONAL_REVIEW"))
    assert result.publication_disposition == "REVIEW"
    assert result.editorial_reason == "geographic_review"
    assert review_events([result]) == [result]


def test_out_of_area_event_is_rejected():
    result = apply_editorial_rules(make_event(geographic_scope="OUT_OF_AREA"))
    assert result.publication_disposition == "REJECT"
    assert result.editorial_reason == "out_of_area"
    assert rejected_events([result]) == [result]


@pytest.mark.parametrize(
    ("city", "region"),
    (("Prosser", "LOWER_VALLEY"), ("Grandview", "LOWER_VALLEY"), ("College Place", "WALLA_WALLA")),
)
def test_out_of_scope_region_is_rejected_without_geographic_review(city, region):
    geography = classify_event({"city": city, "state": "WA"})
    assert geography.region == region
    assert geography.scope == "OUT_OF_AREA"

    result = apply_editorial_rules(
        make_event(city=city, geographic_scope=geography.scope, region=geography.region)
    )

    assert result.publication_disposition == "REJECT"
    assert result.editorial_reason == "out_of_area"
    assert result not in review_events([result])
    assert rejected_events([result]) == [result]


def test_explicit_non_event_content_is_rejected():
    result = apply_editorial_rules(
        make_event(
            content_classification="NAVIGATION",
            content_rejection_reason="pagination_title",
        )
    )
    assert result.publication_disposition == "REJECT"
    assert result.editorial_reason == "pagination_title"
