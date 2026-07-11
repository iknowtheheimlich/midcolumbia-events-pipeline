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
    assert match.method == "alias"
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


def test_richland_library_room_resolves_to_parent_and_preserves_detail():
    registry = VenueRegistry(
        [
            VenueRecord(
                venue_name="Richland Public Library",
                address="955 Northgate Dr, Richland, WA 99352, USA",
                place_id="richland-library",
            )
        ]
    )
    enriched, match = registry.enrich_event(
        {"source": "RichlandLibrary", "venue": "Doris Roberts Gallery", "title": "Art Show"}
    )
    assert match.method == "parent_room"
    assert enriched["venue"] == "Richland Public Library"
    assert enriched["venue_detail"] == "Doris Roberts Gallery"
    assert enriched["venue_id"] == "richland-library"


def test_mcl_parenthetical_branch_name_is_rewritten_deterministically():
    registry = VenueRegistry(
        [
            VenueRecord(
                venue_name="Kennewick Mid-Columbia Library",
                official_name="Mid-Columbia Libraries - Kennewick Branch",
                place_id="kennewick-library",
            )
        ]
    )
    enriched, match = registry.enrich_event(
        {"source": "MidColumbiaLibraries", "venue": "Mid-Columbia Library (Kennewick)"}
    )
    assert match.method == "branch_rewrite"
    assert enriched["venue"] == "Mid-Columbia Libraries - Kennewick Branch"


def test_generic_mcl_name_uses_city_for_unique_branch():
    registry = VenueRegistry(
        [
            VenueRecord(
                venue_name="Pasco Mid-Columbia Library",
                official_name="Mid-Columbia Libraries - Pasco Branch",
            )
        ]
    )
    enriched, match = registry.enrich_event(
        {"source": "MidColumbiaLibraries", "venue": "Mid-Columbia Library", "city": "Pasco"}
    )
    assert match.method == "city_branch"
    assert enriched["venue"] == "Mid-Columbia Libraries - Pasco Branch"


def test_unique_street_address_resolves_registry_record():
    registry = VenueRegistry(
        [
            VenueRecord(
                venue_name="Layered Cake Artistry",
                address="2525 N 20th Ave, Pasco, WA 99301, USA",
                place_id="cake-place",
            )
        ]
    )
    enriched, match = registry.enrich_event({"venue": "2525 N 20th Ave", "city": "Pasco"})
    assert match.method == "venue_as_address"
    assert enriched["venue"] == "Layered Cake Artistry"
    assert enriched["venue_id"] == "cake-place"


def test_ambiguous_street_address_remains_ambiguous():
    registry = VenueRegistry(
        [
            VenueRecord(venue_name="Venue A", address="100 Main St, Pasco, WA 99301, USA"),
            VenueRecord(venue_name="Venue B", address="100 Main St, Kennewick, WA 99336, USA"),
        ]
    )
    enriched, match = registry.enrich_event({"venue": "100 Main St"})
    assert match.status == "ambiguous"
    assert enriched["venue"] == "100 Main St"
