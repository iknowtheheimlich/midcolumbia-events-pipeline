from src.category_intelligence import classify_event, enrich_event_category
from src.venue_category_intelligence import load_venue_category_hints, venue_category_hint


def test_registry_contains_only_promoted_dominant_venue_hints():
    hints = load_venue_category_hints()
    assert hints["art your way"].category == "Classes/Workshops"
    assert hints["alley kat artisans"].category == "Classes/Workshops"
    assert hints["cbc planetarium"].category == "Lectures/Talks"
    assert hints["cpcco planetarium cbc"].category == "Lectures/Talks"
    assert hints["jokers comedy club"].category == "Music/Comedy"
    assert "bookwalter winery" not in hints
    assert "benton county fairgrounds" not in hints


def test_art_your_way_prior_classifies_opaque_project_title():
    decision = classify_event({"title": "Aloha Pineapple", "venue": "Art YOUR Way"})
    assert decision.category == "Classes/Workshops"
    assert decision.confidence == 0.96
    assert decision.reason == "venue_hint=Art YOUR Way;strength=strong"


def test_art_your_way_prior_classifies_paint_your_pet_without_title_keyword_rule():
    decision = classify_event({"title": "Paint Your Pet", "venue_registry_name": "Art YOUR Way"})
    assert decision.category == "Classes/Workshops"
    assert decision.reason.startswith("venue_hint=Art YOUR Way")


def test_observed_alley_kat_alias_classifies_opaque_craft_titles():
    for title in (
        "Make a Kandi Snake",
        "Make Lace Earrings",
        "Making Mandalas",
    ):
        decision = classify_event({"title": title, "venue": "Alley Kat Artisans"})
        assert decision.category == "Classes/Workshops"
        assert decision.confidence == 0.95
        assert decision.reason == "venue_hint=Alley Kat Artisans;strength=strong"


def test_observed_cpcco_planetarium_alias_classifies_opaque_show_titles():
    for title in (
        "The Little Star That Could",
        "Unseen Universe",
        "Black Holes: The Other Side of Infinity",
        "Fractal Explorations",
        "Robot Explorers",
    ):
        decision = classify_event({"title": title, "venue": "CPCCo Planetarium - CBC"})
        assert decision.category == "Lectures/Talks"
        assert decision.confidence == 0.94
        assert decision.reason == "venue_hint=CPCCo Planetarium - CBC;strength=strong"


def test_explicit_fundraiser_title_overrides_art_your_way_prior():
    decision = classify_event({"title": "Community Charity Fundraiser", "venue": "Art YOUR Way"})
    assert decision.category == "Fundraisers"
    assert decision.reason == "title_rule=fundraiser"


def test_explicit_open_mic_title_overrides_hospitality_context():
    decision = classify_event({"title": "Open Mic Night", "venue": "Bookwalter Winery"})
    assert decision.category == "Karaoke/Open Mic"
    assert decision.reason == "title_rule=karaoke_or_open_mic"


def test_existing_source_category_overrides_venue_prior():
    decision = classify_event(
        {"title": "Annual Giving Night", "venue": "Art YOUR Way", "category": "Fundraisers"}
    )
    assert decision.category == "Fundraisers"
    assert decision.reason == "existing_semantic_category"


def test_library_hint_is_low_confidence_and_explainable():
    enriched = enrich_event_category({"title": "Summer Discovery", "venue": "Richland Public Library"})
    assert enriched["category"] == "Community Programs"
    assert enriched["category_confidence"] == 0.63
    assert enriched["category_reason"] == "venue_hint=Richland Public Library;strength=soft"


def test_unknown_multipurpose_venue_has_no_prior():
    event = {"title": "An Extremely Ambiguous Evening", "venue": "Bookwalter Winery"}
    assert venue_category_hint(event) is None
