from src.editorial_style import EditorialStyleProfile, derive_display_fields


def profile() -> EditorialStyleProfile:
    return EditorialStyleProfile(strip_prefixes=("Live Music with", "Live Music w/"), venue_aliases={})


def test_registry_presentation_typo_is_fixed_even_when_venue_is_preserved() -> None:
    title, venue, reason = derive_display_fields(
        "IHB Brews & Tattoos with the Mad Tatter",
        "Ice Harbor BreweryIce",
        "Kennewick",
        category="Music/Comedy",
        profile=profile(),
        preserve_venue=True,
    )
    assert venue == "Ice Harbor Brewery"
    assert "venue_presentation" in reason


def test_spaced_w_slash_is_normalized_after_other_music_cleanup() -> None:
    title, _, _ = derive_display_fields(
        "Catch a Wave w / Badlandz at Clover Island Concert Series",
        "Clover Island Stage",
        "Kennewick",
        category="Music/Comedy",
        profile=profile(),
    )
    assert title == "Catch a Wave / Badlandz"


def test_live_music_on_the_point_is_not_reduced_to_fragment() -> None:
    title, _, _ = derive_display_fields(
        "Live Music on the Point",
        "Riva Riverside Italian Kitchen",
        "Richland",
        category="Music/Comedy",
        profile=profile(),
    )
    assert title == "Live Music on the Point"


def test_frichette_all_white_party_uses_curated_editorial_title() -> None:
    title, _, reason = derive_display_fields(
        'FRICHETTE WINERY "ALL WHITE PARTY',
        "Frichette Winery",
        "Benton City",
        category="Music/Comedy",
        profile=profile(),
    )
    assert title == "Wine en Blanc Soirée"
    assert "title_cleanup" in reason


def test_multilingual_fifa_marketing_copy_uses_english_title() -> None:
    title, _, reason = derive_display_fields(
        "OFFICIAL FIFA WATCH PARTY La fiesta del futbol ven a celebrar!!",
        "John Dam Plaza",
        "Richland",
        category="Events/Hangouts",
        profile=profile(),
    )
    assert title == "FIFA Watch Party"
    assert "title_cleanup" in reason
