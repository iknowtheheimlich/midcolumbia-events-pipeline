from src.intelligence import attach_intelligence, normalize_intelligence, read_intelligence
from src.pipeline import SourceBatch, combine_source_batches
from src.program_intelligence import group_editorial_programs
from src.publisher_editorial import apply_editorial_rules
from src.publisher_projection import project_event
from src.venue_registry import VenueRecord, VenueRegistry


def canonical_event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        "title": "Baby Storytime",
        "start_date": "2026-07-13",
        "end_date": "2026-07-13",
        "start_time": "10:00",
        "end_time": "10:30",
        "venue": "Kennewick Library",
        "city": "Kennewick",
        "state": "WA",
        "url": "https://example.com/event",
        "source": "TestSource",
    }
    event.update(overrides)
    return event


def test_attach_and_read_intelligence_are_additive() -> None:
    event = attach_intelligence({"title": "Event"}, "category", "Music/Comedy", 1.2, "rule")

    assert event["title"] == "Event"
    decision = read_intelligence(event, "category")
    assert decision is not None
    assert decision.value == "Music/Comedy"
    assert decision.confidence == 1.0
    assert decision.reason == "rule"


def test_pipeline_explains_venue_geography_and_category() -> None:
    registry = VenueRegistry(
        [
            VenueRecord(
                venue_name="Kennewick Library",
                official_name="Kennewick Mid-Columbia Library",
                place_id="place-1",
            )
        ]
    )

    enriched = combine_source_batches(
        [SourceBatch("TestSource", [canonical_event()])],
        venue_registry=registry,
        enrich_geography=True,
        enrich_categories=True,
    )[0]

    intelligence = normalize_intelligence(enriched["intelligence"])
    assert intelligence["venue"]["reason"] == "registry_alias"
    assert intelligence["geographic_scope"]["value"] == "LOCAL"
    assert intelligence["category"]["value"] == "Community Programs"


def test_projection_and_editorial_preserve_explanations() -> None:
    event = canonical_event(category="Community Programs", geo_scope="LOCAL", geo_region="TRI_CITIES")
    event = attach_intelligence(event, "category", "Community Programs", 0.94, "keyword=storytime")

    projected = project_event(event)
    editorial = apply_editorial_rules(projected)

    assert projected.intelligence["category"]["reason"] == "keyword=storytime"
    assert editorial.intelligence["category"]["confidence"] == 0.94
    assert editorial.intelligence["display_style"]["reason"] in {"unchanged", "venue_presentation"}


def test_program_grouping_emits_common_explanation() -> None:
    first = apply_editorial_rules(project_event(canonical_event(category="Community Programs", geo_scope="LOCAL")))
    second = apply_editorial_rules(
        project_event(
            canonical_event(
                category="Community Programs",
                geo_scope="LOCAL",
                start_time="11:00",
                end_time="11:30",
                url="https://example.com/event-2",
                source_event_id="2",
            )
        )
    )

    program = group_editorial_programs([first, second])[0]

    assert program.grouping_confidence == 1.0
    assert program.intelligence["program_grouping"]["reason"].startswith("exact_display_title")
