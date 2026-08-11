from src.publisher_editorial import apply_editorial_rules
from src.publisher_projection import project_event
from src.reddit_renderer import render_event_line
from src.venue_presentation import present_event


def event(**overrides):
    values = {
        "title": "Live Music",
        "venue": "Test Venue",
        "city": "Richland",
        "state": "WA",
        "start_date": "2026-07-17",
        "start_time": "19:00",
        "source": "TriCityVibe",
        "url": "https://source.example/event",
        "external_url": "https://source.example/event",
        "category": "Music/Comedy",
        "geo_scope": "LOCAL",
        "content_kind": "EVENT",
    }
    values.update(overrides)
    return values


def test_emerald_variants_share_authoritative_presentation() -> None:
    short = present_event(event(venue="Emerald of Siam"))
    long = present_event(event(venue="The Emerald of Siam"))

    assert short.display_name == long.display_name == "The Emerald of Siam"
    assert short.display_url == long.display_url == "https://www.emeraldofsiam.com/"


def test_solar_spirits_variant_projects_one_name_and_url() -> None:
    projected = project_event(event(venue="Solar Spirits Distillery Tasting Room"))

    assert projected.venue == "Solar Spirits Distillery Tasting Room"
    assert projected.display_venue == "Solar Spirits"
    assert projected.display_url == "https://www.solarspirits.com/"
    assert projected.venue_presentation_reason == "profile_rule"


def test_goose_ridge_presentation_survives_editorial_layer() -> None:
    projected = project_event(
        event(
            title="Angel Urrea at Goose Ridge Winery",
            venue="Goose Ridge Estate Vineyards and Winery",
        )
    )
    editorial = apply_editorial_rules(projected)

    assert editorial.title == "Angel Urrea"
    assert editorial.display_venue == "Goose Ridge Winery"
    assert editorial.publication_url == "https://www.gooseridge.com/"
    assert editorial.intelligence["venue_presentation"]["reason"] == "profile_rule"


def test_notion_combo_remains_authoritative_but_uses_publication_url_path() -> None:
    projected = project_event(
        event(
            venue="Mid-Columbia Libraries - Kennewick Branch",
            venue_registry_name="Kennewick Mid-Columbia Library",
            venue_reddit_combo=(
                "[Kennewick Mid-Columbia Library]"
                "(https://midcolumbialibraries.org/branch/kennewick), Kennewick"
            ),
        )
    )
    editorial = apply_editorial_rules(projected)

    assert editorial.display_venue == "Kennewick Mid-Columbia Library"
    assert editorial.publication_url == "https://midcolumbialibraries.org/branch/kennewick"
    assert editorial.publication_url_reason == "venue_reddit_combo"


def test_allevents_lifted_lotus_fallback_renders_compact_venue_and_city() -> None:
    projected = project_event(
        event(
            title="Recovery Dharma – Weekly Meditation & Discussion at Lifted Lotus",
            venue=(
                "Lifted Lotus Yoga Collective, Kennewick, WA, United States, "
                "Washington 99336"
            ),
            city="Kennewick",
            source="AllEvents",
            source_event_id="200030515870653",
            url="https://allevents.in/kennewick/event/200030515870653",
            external_url=None,
            category="Community Programs",
        )
    )
    editorial = apply_editorial_rules(projected)

    assert projected.display_venue == (
        "Lifted Lotus Yoga Collective, Kennewick, WA, United States, Washington 99336"
    )
    assert editorial.display_venue == "Lifted Lotus Yoga Collective"
    assert render_event_line(editorial) == (
        "Recovery Dharma – Weekly Meditation & Discussion at Lifted Lotus | "
        "[Lifted Lotus Yoga Collective]"
        "(https://allevents.in/kennewick/event/200030515870653), Kennewick | 7p"
    )


def test_allevents_perseid_conflicting_localities_route_to_review() -> None:
    projected = project_event(
        event(
            title="Perseid Meteor Shower Watch Party ☄️",
            venue="Finley, Washington",
            city="Burbank",
            state="WA",
            source="AllEvents",
            source_event_id="200030305782421",
            url="https://allevents.in/burbank/event/200030305782421",
            external_url=None,
            category="Events/Hangouts",
        )
    )
    editorial = apply_editorial_rules(projected)

    assert projected.display_venue == "Finley, Washington"
    assert projected.display_city == "Burbank"
    assert editorial.publication_disposition == "REVIEW"
    assert editorial.editorial_reason == "conflicting_locality_presentation"
    assert editorial.display_city == ""
