from src.category_intelligence import classify_event
from src.editorial_style import EditorialStyleProfile, derive_display_fields


def profile() -> EditorialStyleProfile:
    return EditorialStyleProfile(strip_prefixes=(), venue_aliases={})


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


def test_at_sign_without_space_before_venue_is_removed() -> None:
    title, _, _ = derive_display_fields(
        "Free Agent featuring Zac Grooms @Paperstreet",
        "Paper Street Brewing Co",
        "Richland",
        category="Music/Comedy",
        profile=profile(),
    )
    assert title == "Free Agent / Zac Grooms"


def test_known_performer_spelling_alias_is_canonicalized() -> None:
    title, _, _ = derive_display_fields(
        "Engelwood Heights at the Clover Island Concert Series",
        "Clover Island Stage",
        "Kennewick",
        category="Music/Comedy",
        profile=profile(),
    )
    assert title == "Englewood Heights"


def test_spaced_support_separator_is_normalized() -> None:
    title, _, _ = derive_display_fields(
        "Catch a Wave w / Badlandz at Clover Island Concert Series",
        "Clover Island Stage",
        "Kennewick",
        category="Music/Comedy",
        profile=profile(),
    )
    assert title == "Catch a Wave / Badlandz"


def test_live_at_title_overrides_conflicting_food_category() -> None:
    decision = classify_event(
        event(
            title="Rachel Montgomery LIVE at Solar Spirits",
            category="Food & Drink",
            venue="Solar Spirits",
        )
    )
    assert decision.category == "Music/Comedy"
    assert decision.reason == "title_rule=explicit_live_performance"


def test_saxxidelic_title_overrides_conflicting_food_category() -> None:
    decision = classify_event(
        event(
            title="Joshua Peace Saxxidelic, LIVE at Solar Spirits",
            category="Food & Drink",
            venue="Solar Spirits",
        )
    )
    assert decision.category == "Music/Comedy"
    assert decision.reason == "title_rule=explicit_live_performance"


def test_non_live_food_event_keeps_existing_category() -> None:
    decision = classify_event(
        event(
            title="Wine en Blanc Soiree",
            category="Food & Drink",
            venue="Frichette Winery",
        )
    )
    assert decision.category == "Food & Drink"
