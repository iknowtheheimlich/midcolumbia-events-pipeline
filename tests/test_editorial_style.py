from src.editorial_style import EditorialStyleProfile, derive_display_fields
from src.publisher_editorial import apply_editorial_rules
from src.publisher_projection import PublisherEvent


def profile() -> EditorialStyleProfile:
    return EditorialStyleProfile(
        strip_prefixes=("Live Music ::",),
        venue_aliases={
            "325 east columbia gardens way, kennewick, wa, united states, washington 99336": "Columbia Gardens"
        },
    )


def test_known_raw_address_becomes_curated_venue() -> None:
    title, venue, reason = derive_display_fields(
        "Summer Thursdays at Columbia Gardens",
        "325 East Columbia Gardens Way, Kennewick, WA, United States, Washington 99336",
        "Kennewick",
        profile=profile(),
    )

    assert title == "Summer Thursdays"
    assert venue == "Columbia Gardens"
    assert reason == "venue_presentation+title_cleanup"


def test_unknown_raw_address_is_compacted_not_repeated() -> None:
    title, venue, _ = derive_display_fields(
        "Community Market",
        "123 Main Street, Kennewick, WA 99336",
        "Kennewick",
        profile=profile(),
    )

    assert title == "Community Market"
    assert venue == "123 Main Street"


def test_title_prefix_and_terminal_date_are_display_only() -> None:
    title, venue, reason = derive_display_fields(
        "Live Music :: Frazer Wambeke July 16th",
        "Longship Cellars",
        "Richland",
        profile=profile(),
    )

    assert title == "Frazer Wambeke"
    assert venue == "Longship Cellars"
    assert reason == "title_cleanup"


def test_editorial_event_preserves_canonical_title(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.publisher_editorial.derive_display_fields",
        lambda title, venue, city: ("Summer Thursdays", "Columbia Gardens", "title_cleanup"),
    )
    event = PublisherEvent(
        title="Summer Thursdays at Columbia Gardens",
        start_date="2026-07-16",
        end_date=None,
        start_time="18:00",
        end_time="20:00",
        venue="325 East Columbia Gardens Way, Kennewick, WA 99336",
        parent_venue=None,
        venue_detail=None,
        venue_id=None,
        venue_type=None,
        organization=None,
        city="Kennewick",
        state="WA",
        geographic_scope="LOCAL",
        region="TRI_CITIES",
        location_type="VENUE",
        content_classification="EVENT",
        content_rejection_reason=None,
        source="TestSource",
        source_event_id="1",
        source_url="https://example.com/event",
        source_urls=("https://example.com/event",),
        external_url=None,
        eventbrite_url=None,
        eventbrite_event_id=None,
        category="Events/Hangouts",
        description=None,
        duplicate_sources=(),
        duplicate_count=1,
    )

    result = apply_editorial_rules(event)

    assert result.title == "Summer Thursdays"
    assert result.canonical_title == "Summer Thursdays at Columbia Gardens"
    assert result.display_venue == "Columbia Gardens"
