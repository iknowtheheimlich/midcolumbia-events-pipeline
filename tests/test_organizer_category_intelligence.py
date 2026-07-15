from src.category_intelligence import classify_event, enrich_event_category
from src.organizer_category_intelligence import (
    load_organizer_category_hints,
    normalize_organizer_name,
    organizer_category_hint,
)


def test_registry_loads_aliases_for_promoted_organizers():
    hints = load_organizer_category_hints()
    assert hints["master gardeners"].category == "Classes/Workshops"
    assert hints["dust devils"].category == "Sports"
    assert hints["brma"].category == "Lectures/Talks"


def test_normalization_handles_punctuation_and_ampersands():
    assert normalize_organizer_name("WSU Benton-Franklin Master Gardeners") == "wsu benton franklin master gardeners"
    assert normalize_organizer_name("Research & Education") == "research and education"


def test_master_gardeners_prior_travels_across_venues():
    library = classify_event(
        {
            "title": "Plant Clinic",
            "organizer": "Master Gardeners",
            "venue": "Richland Public Library",
        }
    )
    museum = classify_event(
        {
            "title": "Plant Clinic",
            "organizer": "Master Gardeners",
            "venue": "REACH Museum",
        }
    )
    assert library.category == "Classes/Workshops"
    assert museum.category == "Classes/Workshops"
    assert library.reason == "organizer_hint=WSU Extension Master Gardeners;strength=strong"
    assert museum.reason == library.reason


def test_organizer_prior_precedes_conflicting_venue_prior():
    decision = classify_event(
        {
            "title": "Plant Clinic",
            "organizer": "Master Gardeners",
            "venue": "Richland Public Library",
        }
    )
    assert decision.category == "Classes/Workshops"
    assert decision.reason.startswith("organizer_hint=")


def test_explicit_fundraiser_title_overrides_organizer_prior():
    decision = classify_event(
        {
            "title": "Annual Charity Fundraiser",
            "organizer": "Master Gardeners",
            "venue": "Richland Public Library",
        }
    )
    assert decision.category == "Fundraisers"
    assert decision.reason == "title_rule=fundraiser"


def test_existing_source_category_overrides_organizer_prior():
    decision = classify_event(
        {
            "title": "Community Night",
            "organizer": "Tri-City Dust Devils",
            "category": "Fundraisers",
        }
    )
    assert decision.category == "Fundraisers"
    assert decision.reason == "existing_semantic_category"


def test_dust_devils_prior_classifies_opaque_title():
    enriched = enrich_event_category(
        {
            "title": "First Pitch Friday",
            "organization": "Tri City Dust Devils",
            "venue": "Gesa Stadium",
        }
    )
    assert enriched["category"] == "Sports"
    assert enriched["category_confidence"] == 0.98
    assert enriched["category_reason"] == "organizer_hint=Tri-City Dust Devils;strength=strong"


def test_soft_organizer_hint_is_explainable():
    decision = classify_event(
        {
            "title": "Regional Research Showcase",
            "host": "Washington State University Tri Cities",
            "venue": "CIC",
        }
    )
    assert decision.category == "Lectures/Talks"
    assert decision.confidence == 0.78
    assert decision.reason == "organizer_hint=WSU Tri-Cities;strength=soft"


def test_unknown_organizer_has_no_prior():
    event = {"organizer": "Unregistered Traveling Group"}
    assert organizer_category_hint(event) is None
