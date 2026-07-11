from src.pipeline import SourceBatch, run_pipeline
from src.venue_registry import VenueRecord, VenueRegistry, normalize_venue_key


def test_normalize_venue_key_handles_ampersands_and_punctuation():
    assert normalize_venue_key("Barnard & Griffin Winery!") == "barnard and griffin winery"


def test_registry_matches_alias_and_enriches_missing_fields():
    registry = VenueRegistry(
        [
            VenueRecord(
                venue_name="Tri-Cities Academy of Ballet and Music",
                official_name="Tri-Cities Academy of Ballet",
                address="21 Aaron Dr D, Richland, WA 99352, USA",
                place_id="ChIJ-example",
            )
        ]
    )
    enriched, match = registry.enrich_event(
        {"venue": "Tri-Cities Academy of Ballet and Music", "title": "Recital"}
    )
    assert match.status == "matched"
    assert enriched["venue"] == "Tri-Cities Academy of Ballet"
    assert enriched["venue_id"] == "ChIJ-example"
    assert enriched["address"].startswith("21 Aaron Dr")


def test_registry_does_not_overwrite_existing_event_data():
    registry = VenueRegistry(
        [VenueRecord(venue_name="Venue", official_name="Official Venue", address="Registry Address", place_id="registry-id")]
    )
    enriched, _ = registry.enrich_event(
        {"venue": "Venue", "address": "Event Address", "venue_id": "event-id"}
    )
    assert enriched["venue"] == "Official Venue"
    assert enriched["address"] == "Event Address"
    assert enriched["venue_id"] == "event-id"


def test_ambiguous_alias_is_not_enriched():
    registry = VenueRegistry(
        [
            VenueRecord(venue_name="The Hub", official_name="The Hub Kennewick"),
            VenueRecord(venue_name="The Hub", official_name="The Hub Richland"),
        ]
    )
    event = {"venue": "The Hub", "title": "Market"}
    enriched, match = registry.enrich_event(event)
    assert match.status == "ambiguous"
    assert enriched == event


def test_pipeline_applies_optional_registry_before_publishing():
    registry = VenueRegistry([VenueRecord(venue_name="TC Tee Time", official_name="Tee Time", place_id="place-1")])
    result = run_pipeline(
        [
            SourceBatch(
                source_name="TestSource",
                events=[{"title": "Golf", "venue": "TC Tee Time", "start_date": "2026-07-12"}],
            )
        ],
        venue_registry=registry,
    )
    assert result.all_events[0]["venue"] == "Tee Time"
    assert result.all_events[0]["venue_id"] == "place-1"
