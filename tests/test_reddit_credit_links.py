from src.program_intelligence import group_editorial_programs
from src.publisher_editorial import EditorialEvent
from src.reddit_renderer import render_event_line, render_program_line


def _event(**overrides) -> EditorialEvent:
    values = {
        "title": "Live Music",
        "start_date": "2026-07-15",
        "end_date": None,
        "display_start_time": "18:00",
        "display_end_time": None,
        "display_time": "6p",
        "display_venue": "The Venue",
        "display_city": "Richland",
        "display_organization": "Local Promoter",
        "publication_url": "https://venue.example/",
        "publication_disposition": "AUTO_PUBLISH",
        "editorial_reason": None,
        "publication_target": "MAIN",
        "semantic_category": "Music",
        "source": "Test",
        "source_event_id": "1",
        "venue_id": None,
        "venue_type": None,
        "geographic_scope": "LOCAL",
        "region": None,
        "location_type": None,
        "category": "Music",
        "description": None,
        "eventbrite_event_id": None,
        "duplicate_sources": ("Test",),
        "duplicate_count": 1,
        "display_organization_url": "https://host.example/",
        "display_artist": "The Band",
        "display_artist_url": "https://band.example/",
    }
    values.update(overrides)
    return EditorialEvent(**values)


def test_event_line_links_host_and_artist_without_changing_title() -> None:
    line = render_event_line(_event())

    assert line.startswith("Live Music | [The Venue](https://venue.example/), Richland | 6p")
    assert "Host: [Local Promoter](https://host.example/)" in line
    assert "Artist: [The Band](https://band.example/)" in line


def test_program_line_keeps_shared_credits_once() -> None:
    program = group_editorial_programs([_event(), _event(source_event_id="2", display_start_time="20:00", display_time="8p")])[0]

    line = render_program_line(program)

    assert line.count("Host:") == 1
    assert line.count("Artist:") == 1
    assert "6p • 8p" in line
