from src.pipeline import SourceBatch, combine_source_batches
from src.publisher_editorial import apply_editorial_rules
from src.publisher_projection import project_event
from src.reddit_renderer import render_event_line
from src.venue_registry import VenueRecord, VenueRegistry


def _event() -> dict[str, object]:
    return {
        "title": "LEGO Club",
        "start_date": "2026-07-14",
        "start_time": "16:00",
        "end_time": "17:00",
        "venue": "Mid-Columbia Libraries - Kennewick Branch",
        "city": "Kennewick",
        "url": "https://midcolumbialibraries.org/event/lego-club",
        "source": "MidColumbiaLibraries",
        "category": "Community Programs",
    }


def _registry() -> VenueRegistry:
    return VenueRegistry(
        [
            VenueRecord(
                venue_name="Kennewick Mid-Columbia Library",
                official_name="Mid-Columbia Libraries - Kennewick Branch",
                place_id="place-kennewick-library",
                website="https://midcolumbialibraries.org/branch/kennewick",
                reddit_combo=(
                    "[Kennewick Mid-Columbia Library]"
                    "(https://midcolumbialibraries.org/branch/kennewick), Kennewick"
                ),
            )
        ]
    )


def test_registry_presentation_metadata_does_not_replace_canonical_identity() -> None:
    enriched = combine_source_batches(
        [SourceBatch(source_name="MidColumbiaLibraries", events=[_event()])],
        venue_registry=_registry(),
    )[0]

    assert enriched["venue"] == "Mid-Columbia Libraries - Kennewick Branch"
    assert enriched["venue_id"] == "place-kennewick-library"
    assert enriched["venue_registry_name"] == "Kennewick Mid-Columbia Library"
    assert enriched["venue_website"] == "https://midcolumbialibraries.org/branch/kennewick"
    assert enriched["venue_reddit_combo"].startswith("[Kennewick Mid-Columbia Library]")


def test_notion_reddit_combo_survives_projection_and_renders_unchanged() -> None:
    enriched = combine_source_batches(
        [SourceBatch(source_name="MidColumbiaLibraries", events=[_event()])],
        venue_registry=_registry(),
        enrich_geography=True,
    )[0]

    projected = project_event(enriched)
    editorial = apply_editorial_rules(projected)
    line = render_event_line(editorial)

    assert projected.venue == "Mid-Columbia Libraries - Kennewick Branch"
    assert projected.venue_registry_name == "Kennewick Mid-Columbia Library"
    assert editorial.display_venue == (
        "[Kennewick Mid-Columbia Library]"
        "(https://midcolumbialibraries.org/branch/kennewick), Kennewick"
    )
    assert line == (
        "LEGO Club | [Kennewick Mid-Columbia Library]"
        "(https://midcolumbialibraries.org/branch/kennewick), Kennewick | 4-5p"
    )


def test_plain_venue_fallback_remains_backwards_compatible() -> None:
    projected = project_event(_event())
    editorial = apply_editorial_rules(projected)

    assert editorial.display_venue == "Mid-Columbia Libraries - Kennewick Branch"
    assert render_event_line(editorial) == (
        "LEGO Club | [Mid-Columbia Libraries - Kennewick Branch]"
        "(https://midcolumbialibraries.org/event/lego-club), Kennewick | 4-5p"
    )
