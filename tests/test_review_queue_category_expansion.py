from src.category_intelligence import classify_event


def event(title: str, **overrides):
    row = {
        "title": title,
        "venue": "Test Venue",
        "city": "Richland",
        "start_date": "2026-07-15",
        "url": "https://example.org/event",
        "source": "TestSource",
    }
    row.update(overrides)
    return row


def test_recurring_library_program_titles_classify_as_community_programs() -> None:
    for title in (
        "Music Together",
        "Library Gaming Guild",
        "Meet Our Therapy Dogs",
        "Love on a Leash",
    ):
        decision = classify_event(event(title))
        assert decision.category == "Community Programs"
        assert decision.reason == "title_rule=library_or_community_program"


def test_book_talk_uses_existing_lecture_category() -> None:
    decision = classify_event(event("Community Program: Book Talk"))
    assert decision.category == "Lectures/Talks"
    assert decision.reason == "title_rule=lecture_or_history_talk"


def test_library_source_audience_categories_map_into_existing_taxonomy() -> None:
    kids = classify_event(event("Music Together", source_category="Kids and Families"))
    adult = classify_event(event("B Reactor Museum Association Presents: Ice Age Floods", source_category="Adult"))
    assert kids.category == "Community Programs"
    assert adult.category == "Community Programs"


def test_repeated_faith_programs_classify_without_new_taxonomy() -> None:
    for title in ("Vacation Bible School", "Tri-Ward Youth Activity Night"):
        decision = classify_event(event(title))
        assert decision.category == "Faith Based"
        assert decision.reason == "title_rule=religious_program"


def test_participatory_art_review_titles_are_classes() -> None:
    for title in ("Kiddo and Adult Paint a Ceramic Piece", "Summer Shenanigans: Cartoon Creation"):
        decision = classify_event(event(title))
        assert decision.category == "Classes/Workshops"
        assert decision.reason == "title_rule=participatory_visual_art"


def test_auditions_are_art_theater() -> None:
    decision = classify_event(event("Auditions: Steel Magnolias"))
    assert decision.category == "Art/Theater"
    assert decision.reason == "title_rule=film_or_theater"


def test_live_music_source_category_maps_to_music_comedy() -> None:
    decision = classify_event(event("Blue Heron at Perch Cantina", source_category="Live Music"))
    assert decision.category == "Music/Comedy"
    assert decision.reason == "source_category=Live Music"
