from src.category_intelligence import classify_event


def event(title: str) -> dict[str, object]:
    return {
        "title": title,
        "venue": "Test Venue",
        "city": "Richland",
        "start_date": "2026-07-20",
        "url": "https://example.org/event",
        "source": "TestSource",
        "geo_scope": "LOCAL",
        "content_kind": "EVENT",
    }


def test_repeated_library_activity_titles_are_classified() -> None:
    expected = {
        "Creative Kids: Perler Beads": "Classes/Workshops",
        "Paint-A-Saurus": "Classes/Workshops",
        "Fiber & Friends": "Classes/Workshops",
        "T-shirt Memory Quilt/ monthly block": "Classes/Workshops",
        "Gaming Guild": "Trivia/Game Night",
    }

    for title, category in expected.items():
        decision = classify_event(event(title))
        assert decision.category == category, title


def test_obvious_instruction_and_health_titles_are_classified() -> None:
    expected = {
        "CPR/AED & First Aid Certification": "Classes/Workshops",
        "Into to Tarot with Shannon McBride": "Classes/Workshops",
        "Chronic Heart Failure Education": "Lectures/Talks",
    }

    for title, category in expected.items():
        decision = classify_event(event(title))
        assert decision.category == category, title


def test_obvious_sports_theater_faith_and_community_titles_are_classified() -> None:
    expected = {
        "Race #8": "Sports",
        "Alumni Game": "Sports",
        "Disney's Newsies": "Art/Theater",
        "FHE/ Noche de Hogar Barrio": "Faith Based",
        "Second Harvest Fil-Am Group Volunteer Event for 12+ years old": "Community Programs",
        "Quake - Tuesday, July 21 - $7 Sensory Friendly Night": "Community Programs",
    }

    for title, category in expected.items():
        decision = classify_event(event(title))
        assert decision.category == category, title


def test_rules_do_not_overgeneralize_ambiguous_words() -> None:
    for title in (
        "A Race Against Time",
        "Game Developers Networking",
        "Painting the Future of Healthcare",
        "Education Funding Committee Meeting",
    ):
        decision = classify_event(event(title))
        assert decision.category is None, title
