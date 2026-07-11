from src.geography import (
    GeoPoint,
    city_state_from_address,
    classify_event,
    classify_region,
    enrich_event_geography,
    haversine_miles,
    normalize_city,
)
from src.pipeline import SourceBatch, run_pipeline


def test_normalize_city_repairs_known_misspelling():
    assert normalize_city("Herminston") == "Hermiston"


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


def test_regional_and_out_of_area_regions_are_distinct():
    assert classify_region("Prosser", "WA") == "LOWER_VALLEY"
    assert classify_region("Yakima", "WA") == "YAKIMA"
    assert classify_event({"city": "Prosser", "state": "WA"}).scope == "REGIONAL_REVIEW"
    assert classify_event({"city": "Yakima", "state": "WA"}).scope == "OUT_OF_AREA"


def test_unknown_location_is_review_not_rejected():
    result = classify_event({"venue": "Mystery Hall"})
    assert result.region == "UNKNOWN"
    assert result.scope == "REVIEW"


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
