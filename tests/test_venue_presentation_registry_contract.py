from src.publisher_editorial import apply_editorial_rules
from src.publisher_projection import project_event
from src.venue_registry import VenueRecord, VenueRegistry


def source_event(**overrides):
    event = {
        "title": "Angel Urrea at Goose Ridge Winery",
        "venue": "Goose Ridge Estate Vineyards and Winery",
        "city": "Richland",
        "state": "WA",
        "start_date": "2026-07-17",
        "start_time": "17:00",
        "source": "TriCityVibe",
        "url": "https://source.example/angel",
        "external_url": "https://source.example/angel",
        "category": "Music/Comedy",
        "geo_scope": "LOCAL",
        "content_kind": "EVENT",
    }
    event.update(overrides)
    return event


def test_registry_record_enriches_authoritative_presentation_fields() -> None:
    registry = VenueRegistry(
        [
            VenueRecord(
                venue_name="Goose Ridge Winery",
                official_name="Goose Ridge Estate Vineyards and Winery",
                place_id="goose-ridge-place",
                website="https://legacy.example/goose",
                display_name="Goose Ridge Winery",
                display_url="https://www.gooseridge.com/",
                display_city="Richland",
                short_name="Goose Ridge",
                venue_type="Winery",
            )
        ]
    )

    enriched, match = registry.enrich_event(source_event())

    assert match.status == "matched"
    assert enriched["venue"] == "Goose Ridge Estate Vineyards and Winery"
    assert enriched["venue_registry_name"] == "Goose Ridge Winery"
    assert enriched["display_venue"] == "Goose Ridge Winery"
    assert enriched["display_url"] == "https://www.gooseridge.com/"
    assert enriched["display_city"] == "Richland"
    assert enriched["venue_short_name"] == "Goose Ridge"
    assert enriched["venue_presentation_reason"] == "registry_presentation"


def test_projection_prefers_registry_fields_over_compatibility_profile() -> None:
    projected = project_event(
        source_event(
            venue_registry_name="Goose Ridge Winery",
            display_venue="Goose Ridge Amphitheater",
            display_url="https://example.org/authoritative",
            display_city="Benton City",
            suppress_display_city=True,
            venue_presentation_reason="registry_presentation",
        )
    )

    assert projected.venue == "Goose Ridge Estate Vineyards and Winery"
    assert projected.display_venue == "Goose Ridge Amphitheater"
    assert projected.display_url == "https://example.org/authoritative"
    assert projected.display_city is None
    assert projected.venue_presentation_reason == "registry_presentation"


def test_registry_presentation_survives_editorial_and_title_cleanup() -> None:
    projected = project_event(
        source_event(
            display_venue="Goose Ridge Winery",
            display_url="https://www.gooseridge.com/",
            display_city="Richland",
            venue_presentation_reason="registry_presentation",
        )
    )

    editorial = apply_editorial_rules(projected)

    assert editorial.title == "Angel Urrea"
    assert editorial.display_venue == "Goose Ridge Winery"
    assert editorial.publication_url == "https://www.gooseridge.com/"
    assert editorial.intelligence["venue_presentation"]["reason"] == "registry_presentation"
