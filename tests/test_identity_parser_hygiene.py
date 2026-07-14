from adapters.richland_library.parser import clean_title
from src.editorial_style import EditorialStyleProfile, derive_display_fields


def profile() -> EditorialStyleProfile:
    return EditorialStyleProfile(
        strip_prefixes=(),
        venue_aliases={"ice harbor breweryice": "Ice Harbor Brewery"},
    )


def test_known_performer_pair_has_stable_order() -> None:
    first, _, _ = derive_display_fields(
        "Free Agent featuring Zac Grooms",
        "Paper Street Brewing Co",
        "Richland",
        category="Music/Comedy",
        profile=profile(),
    )
    second, _, _ = derive_display_fields(
        "Zac Grooms w / Free Agent",
        "Paper Street Brewing Co",
        "Richland",
        category="Music/Comedy",
        profile=profile(),
    )
    assert first == second == "Free Agent / Zac Grooms"


def test_libcal_repeated_accessibility_fragments_are_removed_at_parser_boundary() -> None:
    assert clean_title(
        "Family Movies ofFamily Movies of the 1990s: Jumanji, The Sandlot, and Matilda"
    ) == "Family Movies of the 1990s: Jumanji, The Sandlot, and Matilda"


def test_known_concatenated_venue_alias_is_cleaned() -> None:
    _, venue, reason = derive_display_fields(
        "Brews & Tattoos",
        "Ice Harbor BreweryIce",
        "Kennewick",
        category="Events/Hangouts",
        profile=profile(),
    )
    assert venue == "Ice Harbor Brewery"
    assert reason == "venue_presentation"


def test_unrelated_collaboration_order_is_preserved() -> None:
    title, _, _ = derive_display_fields(
        "Alpha w/ Beta",
        "Example Venue",
        "Richland",
        category="Music/Comedy",
        profile=profile(),
    )
    assert title == "Alpha / Beta"
