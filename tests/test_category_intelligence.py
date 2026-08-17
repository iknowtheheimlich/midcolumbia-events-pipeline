import pytest

from src.category_intelligence import classify_event, enrich_event_category
from src.pipeline import SourceBatch, run_pipeline


def event(**overrides):
    values = {
        "title": "Untitled Event",
        "venue": "Test Venue",
        "city": "Richland",
        "start_date": "2026-07-15",
        "url": "https://example.org/event",
        "source": "TestSource",
        "geo_scope": "LOCAL",
        "content_kind": "EVENT",
    }
    values.update(overrides)
    return values


def test_preserves_existing_semantic_category() -> None:
    decision = classify_event(event(category="Sports", title="Mystery"))
    assert decision.category == "Sports"
    assert decision.confidence == 1.0
    assert decision.reason == "existing_semantic_category"


def test_classifies_storytime_as_community_program() -> None:
    decision = classify_event(event(title="Baby Storytime With Ms. Amy", organizer="Mid-Columbia Libraries"))
    assert decision.category == "Community Programs"
    assert decision.confidence >= 0.9
    assert decision.reason == "title_rule=library_or_community_program"


def test_classifies_open_mic_before_generic_music() -> None:
    decision = classify_event(event(title="Live Music Open Mic at Emerald"))
    assert decision.category == "Karaoke/Open Mic"
    assert decision.reason == "title_rule=karaoke_or_open_mic"


def test_classifies_source_category_without_copying_source_vocabulary() -> None:
    decision = classify_event(event(title="Unknown", source_category="Food & Drink"))
    assert decision.category == "Food & Drink"
    assert decision.reason == "source_category=Food & Drink"


def test_unmatched_event_stays_unclassified_and_explained() -> None:
    decision = classify_event(event(title="An Extremely Ambiguous Thing"))
    assert decision.category is None
    assert decision.confidence == 0.0
    assert decision.reason == "no_category_rule_matched"


def test_enrichment_is_additive_and_does_not_mutate_input() -> None:
    original = event(title="Tri-City Dust Devils Game")
    enriched = enrich_event_category(original)
    assert "category" not in original
    assert enriched["category"] == "Sports"
    assert enriched["category_confidence"] > 0
    assert enriched["category_reason"] == "title_rule=sports_competition"


def test_pipeline_category_enrichment_is_opt_in_for_backwards_compatibility() -> None:
    batch = SourceBatch("TestSource", [event(title="Open Mic")])
    legacy = run_pipeline([batch])
    enriched = run_pipeline([batch], enrich_categories=True)
    assert legacy.all_events[0].get("category") is None
    assert enriched.all_events[0]["category"] == "Karaoke/Open Mic"


def test_category_explanation_survives_projection_and_editorial_layers() -> None:
    pipeline = run_pipeline(
        [SourceBatch("TestSource", [event(title="Open Mic")])],
        enrich_categories=True,
    )
    projected = pipeline.publisher_projection[0]
    editorial = pipeline.editorial_projection[0]
    assert projected.category_reason == "title_rule=karaoke_or_open_mic"
    assert projected.category_confidence == 0.99
    assert editorial.category_reason == "title_rule=karaoke_or_open_mic"
    assert editorial.semantic_category == "Karaoke/Open Mic"
    assert editorial.publication_target == "MAIN"


def test_play_is_not_a_bare_art_theater_trigger() -> None:
    decision = classify_event(event(title="Summer Chess Classes Learn & Play"))
    assert decision.category == "Classes/Workshops"
    assert decision.reason == "title_rule=explicit_class_or_workshop"


def test_stage_play_remains_art_theater() -> None:
    decision = classify_event(event(title="Bluey's Big Stage Play"))
    assert decision.category == "Art/Theater"
    assert decision.reason == "title_rule=film_or_theater"


def test_history_presentation_is_a_lecture() -> None:
    decision = classify_event(
        event(title="The Triple Nickel: Black Paratroopers in Washington State, 1945")
    )
    assert decision.category == "Lectures/Talks"


def test_family_movies_are_not_sports() -> None:
    decision = classify_event(
        event(title="Family Movies of the 1990s: Jumanji, The Sandlot, and Matilda")
    )
    assert decision.category == "Art/Theater"


def test_food_pairing_gets_food_and_drink_category() -> None:
    decision = classify_event(event(title="Peaches + Cream Cake Pairing Flight"))
    assert decision.category == "Food & Drink"


def test_live_performer_title_beats_class_language_in_description() -> None:
    decision = classify_event(
        event(
            title="Joshua Peace Saxxidelic, LIVE at Solar Spirits!",
            venue="Solar Spirits",
            description="This class of performer brings a playful sound to the tasting room.",
        )
    )
    assert decision.category == "Music/Comedy"


def test_performer_named_faith_is_not_religious() -> None:
    decision = classify_event(
        event(title="Faith Martin @ At Michele's", venue="At Michele's", description="Faith Martin performing live")
    )
    assert decision.category == "Music/Comedy"
    assert decision.reason == "semantic_rule=explicit_musical_performance"


def test_participatory_visual_art_is_a_class_even_at_a_winery() -> None:
    decision = classify_event(
        event(
            title="Spring Flowers Painting with Glass | Fused Glass db Studio",
            venue="Barnard Griffin Winery",
            source_category="Music",
        )
    )
    assert decision.category == "Classes/Workshops"
    assert decision.reason == "title_rule=participatory_visual_art"


def test_suncatcher_is_a_class_not_presented_art() -> None:
    decision = classify_event(
        event(title="KIDS! Suncatcher | Fused Glass db Studio", venue="Barnard Griffin Winery")
    )
    assert decision.category == "Classes/Workshops"
    assert decision.reason == "title_rule=participatory_visual_art"


def test_visiting_winemaker_outranks_hospitality_music_context() -> None:
    decision = classify_event(
        event(
            title="Visiting Winemaker Night from Frichette at Solar Spirits",
            venue="Solar Spirits",
            source_category="Music",
        )
    )
    assert decision.category == "Food & Drink"
    assert decision.reason == "title_rule=explicit_food_or_winemaker_event"


def test_explicit_class_can_correct_conflicting_existing_category() -> None:
    decision = classify_event(
        event(title="Adult Intro to Hip Hop Dance Class", category="Music/Comedy")
    )
    assert decision.category == "Classes/Workshops"
    assert decision.reason == "title_rule=explicit_class_or_workshop"


@pytest.mark.parametrize(
    ("payload", "category"),
    [
        ({"title": "Gaming Guild", "description": "Tabletop games and creativity.", "source": "MidColumbiaLibraries"}, "Community Programs"),
        ({"title": "Chamber Luncheon", "description": "Monthly networking luncheon."}, "Events/Hangouts"),
        ({"title": "Hidden Layers", "description": "In this talk, explore social history.", "venue": "City Museum", "venue_type": "museum"}, "Lectures/Talks"),
        ({"title": "Pumpkin Stitch", "description": "An instructor will guide you through creating a pumpkin."}, "Classes/Workshops"),
        ({"title": "Sapphic Sugar Cabaret", "description": "A burlesque show."}, "Art/Theater"),
        ({"title": "Recovery Dharma", "description": "A supportive gathering and meditation.", "organizer": "Private Yoga Collective"}, "Events/Hangouts"),
        ({"title": "Silent Auction", "description": "A silent auction to support Jane's cancer care."}, "Fundraisers"),
        ({"title": "Relief Society and Elders Quorum", "description": "A ward program.", "venue": "LDS Church"}, "Faith Based"),
        ({"title": "Women's Night Out", "description": "Test your Bible knowledge during trivia with the GracePoint family."}, "Faith Based"),
        ({"title": "Three Bands Tonight", "description": "A three bands mini music festival."}, "Music/Comedy"),
        ({"title": "Surplus Sale", "description": "Items sold as-is; buyers must remove purchases."}, "Estate/Yard/Garage Sales"),
    ],
)
def test_approved_durable_semantic_evidence(payload, category):
    assert classify_event(payload).category == category


def test_trusted_library_fallback_does_not_extend_to_private_library_venue():
    decision = classify_event({"title": "Creative Gathering", "description": "A program.", "source": "AllEvents", "venue": "Private Library Cafe", "organizer": "Cafe LLC"})
    assert decision.category != "Community Programs"


def test_faith_venue_without_program_evidence_stays_unknown():
    assert classify_event({"title": "Open House", "venue": "Example Church"}).category is None


def test_generic_promotion_stays_unknown():
    assert classify_event({"title": "Product Showcase", "description": "Discover exciting innovation."}).category is None
