from src.program_intelligence import group_editorial_programs
from src.publisher_editorial import EditorialEvent
from src.reddit_renderer import render_program_line


def editorial_event(**overrides: object) -> EditorialEvent:
    values = {
        "title": "Magna-Saurus",
        "start_date": "2026-07-14",
        "end_date": "2026-07-14",
        "display_start_time": "10:30",
        "display_end_time": "11:30",
        "display_time": "10:30-11:30a",
        "display_venue": "Pasco Mid-Columbia Library",
        "display_city": "Pasco",
        "display_organization": None,
        "publication_url": "https://example.com/pasco",
        "publication_disposition": "AUTO_PUBLISH",
        "editorial_reason": None,
        "publication_target": "MAIN",
        "semantic_category": "Community Programs",
        "source": "MidColumbiaLibraries",
        "source_event_id": "one",
        "venue_id": "pasco",
        "venue_type": "Library",
        "geographic_scope": "LOCAL",
        "region": "TRI_CITIES",
        "location_type": "VENUE",
        "category": "Community Programs",
        "description": None,
        "eventbrite_event_id": None,
        "duplicate_sources": (),
        "duplicate_count": 1,
        "category_confidence": 0.98,
        "category_reason": "keyword=magna-saurus",
        "canonical_title": "Magna-Saurus",
        "style_reason": "unchanged",
    }
    values.update(overrides)
    return EditorialEvent(**values)


def test_groups_same_program_across_branches_and_times() -> None:
    programs = group_editorial_programs(
        [
            editorial_event(),
            editorial_event(
                display_start_time="13:00",
                display_end_time="14:00",
                display_time="1-2p",
                display_venue="Keewaydin Park Mid-Columbia Library",
                display_city="Kennewick",
                publication_url="https://example.com/keewaydin",
                source_event_id="two",
                venue_id="keewaydin",
            ),
        ]
    )

    assert len(programs) == 1
    assert len(programs[0].occurrences) == 2
    assert programs[0].grouping_reason == "multiple_venues+multiple_times"


def test_does_not_group_same_title_from_different_sources() -> None:
    programs = group_editorial_programs(
        [editorial_event(), editorial_event(source="OtherSource", source_event_id="two")]
    )

    assert len(programs) == 2


def test_does_not_group_same_title_on_different_dates() -> None:
    programs = group_editorial_programs(
        [editorial_event(), editorial_event(start_date="2026-07-15", source_event_id="two")]
    )

    assert len(programs) == 2


def test_renders_multi_venue_occurrence_chain() -> None:
    program = group_editorial_programs(
        [
            editorial_event(),
            editorial_event(
                display_start_time="13:00",
                display_end_time="14:00",
                display_time="1-2p",
                display_venue="Keewaydin Park Mid-Columbia Library",
                display_city="Kennewick",
                publication_url="https://example.com/keewaydin",
                source_event_id="two",
            ),
        ]
    )[0]

    line = render_program_line(program)

    assert line.startswith("Magna-Saurus | ")
    assert "Pasco Mid-Columbia Library" in line
    assert "10:30-11:30a" in line
    assert "Keewaydin Park Mid-Columbia Library" in line
    assert "1-2p" in line
    assert " • " in line


def test_single_occurrence_preserves_existing_line_shape() -> None:
    program = group_editorial_programs([editorial_event()])[0]

    assert render_program_line(program) == (
        "Magna-Saurus | [Pasco Mid-Columbia Library](https://example.com/pasco), Pasco | "
        "10:30-11:30a"
    )
