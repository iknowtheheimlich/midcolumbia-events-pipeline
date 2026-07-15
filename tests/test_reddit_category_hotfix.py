from tests.test_reddit_renderer import editorial_event

from src.reddit_renderer import render_reddit_post


def test_default_render_includes_profile_category_headers() -> None:
    post = render_reddit_post(
        [
            editorial_event(title="Concert", semantic_category="Music/Comedy", category="Live Music"),
            editorial_event(title="Dinner", semantic_category="Food & Drink", category="Food & Drink"),
        ],
        footnote="",
    )

    assert "## Music/Comedy" in post
    assert "## Food & Drink" in post
    assert post.index("## Music/Comedy") < post.index("## Food & Drink")


def test_render_places_blank_line_between_events() -> None:
    post = render_reddit_post(
        [
            editorial_event(title="First", semantic_category="Music/Comedy"),
            editorial_event(title="Second", semantic_category="Music/Comedy"),
        ],
        footnote="",
    )

    first_line = next(line for line in post.splitlines() if line.startswith("First |"))
    second_line = next(line for line in post.splitlines() if line.startswith("Second |"))
    assert f"{first_line}\n\n{second_line}" in post
