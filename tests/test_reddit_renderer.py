from __future__ import annotations

from pathlib import Path

import pytest

from src.publisher_editorial import EditorialEvent
from src.reddit_renderer import (
    default_artifact_path,
    default_community_artifact_path,
    default_main_artifact_path,
    render_event_line,
    render_reddit_post,
    write_reddit_artifact,
)


def editorial_event(**overrides: object) -> EditorialEvent:
    values = {
        "title": "Science Night",
        "start_date": "2026-07-12",
        "end_date": None,
        "display_start_time": "18:00",
        "display_end_time": None,
        "display_time": "6p",
        "display_venue": "Richland Library",
        "display_city": "Richland",
        "display_organization": None,
        "publication_url": "https://example.com/science-night",
        "publication_disposition": "AUTO_PUBLISH",
        "editorial_reason": None,
        "publication_target": "MAIN",
        "semantic_category": "Events/Hangouts",
        "source": "RichlandLibrary",
        "source_event_id": "science-1",
        "venue_id": "place-1",
        "venue_type": "Library",
        "geographic_scope": "LOCAL",
        "region": "TRI_CITIES",
        "location_type": "VENUE",
        "category": "Events/Hangouts",
        "description": None,
        "eventbrite_event_id": None,
        "duplicate_sources": (),
        "duplicate_count": 1,
    }
    values.update(overrides)
    return EditorialEvent(**values)


def test_render_event_line_preserves_reddit_contract() -> None:
    line = render_event_line(editorial_event())

    assert line == (
        "Science Night | [Richland Library](https://example.com/science-night), "
        "Richland | 6p"
    )


@pytest.mark.parametrize(
    "destination",
    [
        "https://Facebook",
        "https://www.academyofchildrenstheatre.org/https://app.arts-people.com/index.php",
    ],
)
def test_final_artifact_rejects_malformed_markdown_destinations(destination: str) -> None:
    with pytest.raises(ValueError, match="Markdown destination"):
        render_event_line(editorial_event(publication_url=destination))


def test_render_event_line_supports_compact_time_range() -> None:
    line = render_event_line(editorial_event(display_end_time="20:00", display_time="6-8p"))

    assert line.endswith("6-8p")


def test_render_post_groups_by_date_and_sorts_time() -> None:
    post = render_reddit_post(
        [
            editorial_event(title="Ten", display_start_time="10:00", display_time="10a"),
            editorial_event(title="Nine", display_start_time="09:00", display_time="9a"),
            editorial_event(
                title="Tomorrow",
                start_date="2026-07-13",
                display_start_time="13:00",
                display_time="1p",
            ),
        ],
        footnote="",
    )

    assert post.startswith("#12 July\n\n")
    assert post.index("Nine") < post.index("Ten") < post.index("#13 July")


def test_render_post_uses_profile_category_order_within_date() -> None:
    post = render_reddit_post(
        [
            editorial_event(title="Concert", semantic_category="Music/Comedy"),
            editorial_event(title="Market", semantic_category="Markets"),
        ],
        category_order=("Markets", "Music/Comedy"),
        footnote="",
    )

    assert post.index("## Markets") < post.index("Market") < post.index("## Music/Comedy")
    assert post.index("## Music/Comedy") < post.index("Concert")


def test_render_post_preserves_categories_missing_from_profile() -> None:
    post = render_reddit_post(
        [
            editorial_event(
                title="Known Event",
                semantic_category="Events/Hangouts",
            ),
            editorial_event(
                title="Unexpected Event",
                semantic_category="Community Event",
                category="Community Event",
            ),
        ],
        category_order=("Events/Hangouts",),
        footnote="",
    )

    assert "Known Event" in post
    assert "## Community Event" in post
    assert "Unexpected Event" in post


def test_render_post_excludes_review_and_rejected_events() -> None:
    post = render_reddit_post(
        [
            editorial_event(title="Published"),
            editorial_event(title="Review", publication_disposition="REVIEW"),
            editorial_event(title="Rejected", publication_disposition="REJECT"),
        ],
        footnote="",
    )

    assert "Published" in post
    assert "Review" not in post
    assert "Rejected" not in post


def test_render_post_appends_standard_footnote() -> None:
    post = render_reddit_post([editorial_event()])

    assert post.endswith(
        "This is not an all inclusive list. Events were extracted from allevents.in, "
        "visittri-cities.com, tricityvibe.com.\n"
    )


def test_write_artifact_creates_parent_directory(tmp_path: Path) -> None:
    output = tmp_path / "artifacts" / "reddit" / "post.txt"

    result = write_reddit_artifact([editorial_event()], output)

    assert result == output
    assert output.read_text(encoding="utf-8").startswith("#12 July")


def test_write_artifact_rejects_fixture_path(tmp_path: Path) -> None:
    output = tmp_path / "fixtures" / "generated_post.txt"

    with pytest.raises(ValueError, match="separate from fixtures"):
        write_reddit_artifact([editorial_event()], output)


def test_default_artifact_path_is_outside_fixtures() -> None:
    path = default_artifact_path(__import__("datetime").date(2026, 7, 12))

    assert path == Path("artifacts/reddit/reddit_post_2026-07-12.txt")
    assert "fixtures" not in path.parts


def test_dual_default_artifact_paths_use_stable_names() -> None:
    assert default_main_artifact_path() == Path("artifacts/reddit/Main_Events_Post.txt")
    assert default_community_artifact_path() == Path("artifacts/reddit/Community_Events_Post.txt")
