from src.category_intelligence import classify_event


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


def test_visual_art_title_corrects_conflicting_music_category() -> None:
    decision = classify_event(
        event(
            title="Spring Flowers Painting with Glass | Fused Glass db Studio",
            category="Music/Comedy",
        )
    )
    assert decision.category == "Art/Theater"
    assert decision.reason == "correction_rule=explicit_visual_art_activity"


def test_explicit_class_corrects_conflicting_music_source_category() -> None:
    decision = classify_event(
        event(
            title="KIDS! Suncatcher Class | Fused Glass db Studio",
            source_category="music",
        )
    )
    assert decision.category == "Classes/Workshops"
    assert decision.reason == "correction_rule=explicit_class_or_workshop"


def test_winemaker_event_corrects_conflicting_music_category() -> None:
    decision = classify_event(
        event(
            title="Visiting Winemaker Night from Frichette at Solar Spirits",
            category="Music/Comedy",
        )
    )
    assert decision.category == "Food & Drink"
    assert decision.reason == "correction_rule=explicit_food_or_winemaker_event"


def test_unrelated_existing_category_is_still_preserved() -> None:
    decision = classify_event(event(title="Mystery Event", category="Sports"))
    assert decision.category == "Sports"
    assert decision.reason == "existing_semantic_category"
