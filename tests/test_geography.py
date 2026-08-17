from src.geography import (
    GeoPoint,
    LOWER_VALLEY,
    WALLA_WALLA,
    city_state_from_address,
    classify_event,
    classify_region,
    enrich_event_geography,
    haversine_miles,
    looks_like_street_location,
    normalize_city,
)
from src.pipeline import SourceBatch, run_pipeline


def test_normalize_city_repairs_known_misspelling():
    assert normalize_city("Herminston") == "Hermiston"


def test_unknown_city_normalizes_to_missing():
    assert normalize_city("Unknown") is None


def test_city_state_is_extracted_from_address():
    city, state = city_state_from_address("955 Northgate Dr, Richland, WA 99352, USA")
    assert city == "Richland"
    assert state == "WA"


def test_full_state_name_is_extracted_from_address():
    city, state = city_state_from_address(
        "2525 N 20th Ave, Pasco, Washington 99301, United States"
    )
    assert city == "Pasco"
    assert state == "WA"


def test_tri_cities_city_is_local():
    result = classify_event({"city": "Kennewick", "state": "Washington"})
    assert result.region == "TRI_CITIES"
    assert result.scope == "LOCAL"


def test_tri_cities_label_is_local_without_inventing_one_city():
    result = classify_event({"city": "Tri-Cities", "state": "WA"})
    assert result.region == "TRI_CITIES"
    assert result.scope == "LOCAL"


def test_lower_valley_cities_are_outside_publication_scope():
    assert {classify_event({"city": city, "state": "WA"}).scope for city in LOWER_VALLEY} == {
        "OUT_OF_AREA"
    }
    assert classify_region("Prosser", "WA") == "LOWER_VALLEY"
    assert classify_region("Grandview", "WA") == "LOWER_VALLEY"


def test_walla_walla_cities_are_outside_publication_scope():
    assert {classify_event({"city": city, "state": "WA"}).scope for city in WALLA_WALLA} == {
        "OUT_OF_AREA"
    }
    assert classify_region("College Place", "WA") == "WALLA_WALLA"


def test_known_out_of_area_regions_remain_distinct():
    assert classify_region("Prosser", "WA") == "LOWER_VALLEY"
    assert classify_region("Yakima", "WA") == "YAKIMA"
    assert classify_event({"city": "Prosser", "state": "WA"}).scope == "OUT_OF_AREA"
    assert classify_event({"city": "Yakima", "state": "WA"}).scope == "OUT_OF_AREA"


def test_unknown_location_is_review_not_rejected():
    result = classify_event({"venue": "Mystery Hall"})
    assert result.region == "UNKNOWN"
    assert result.scope == "REVIEW"


def test_numbered_venue_is_preserved_as_private_address():
    event = {
        "venue": "430 George Washington Way",
        "city": "430 George",
        "address": "430 George Washington Way, Richland, WA 99352",
    }
    enriched = enrich_event_geography(event)
    assert enriched["venue"] == "430 George Washington Way"
    assert enriched["city"] == "Richland"
    assert enriched["geo_scope"] == "LOCAL"
    assert enriched["location_type"] == "PRIVATE_ADDRESS"


def test_truncated_street_city_without_full_address_stays_review():
    enriched = enrich_event_geography({"venue": "812 W.", "city": "812 W."})
    assert "city" not in enriched
    assert enriched["geo_scope"] == "REVIEW"
    assert enriched["location_type"] == "PRIVATE_ADDRESS"


def test_named_venue_with_address_is_not_labeled_private():
    result = classify_event(
        {
            "venue": "Benton County Fairgrounds",
            "address": "812 W Washington St, Pasco, WA 99301",
        }
    )
    assert result.location_type == "VENUE"
    assert result.city == "Pasco"


def test_street_location_detection_requires_numbered_prefix():
    assert looks_like_street_location("430 George Washington Way")
    assert not looks_like_street_location("George Washington Way")


def test_haversine_returns_reasonable_tri_cities_distance():
    richland = GeoPoint(46.2857, -119.2845)
    kennewick = GeoPoint(46.2112, -119.1372)
    distance = haversine_miles(richland, kennewick)
    assert 7 < distance < 10


def test_coordinate_enrichment_adds_distances():
    enriched = enrich_event_geography(
        {"city": "Richland", "latitude": 46.2857, "longitude": -119.2845}
    )
    assert enriched["geo_region"] == "TRI_CITIES"
    assert enriched["distance_to_richland_miles"] == 0.0
    assert enriched["distance_to_kennewick_miles"] > 0


def test_pipeline_geography_is_optional_and_explicit():
    batch = SourceBatch(
        source_name="TestSource",
        events=[{"title": "Market", "city": "Pasco", "start_date": "2026-07-12"}],
    )
    plain = run_pipeline([batch])
    enriched = run_pipeline([batch], enrich_geography=True)
    assert "geo_region" not in plain.all_events[0]
    assert enriched.all_events[0]["geo_region"] == "TRI_CITIES"
