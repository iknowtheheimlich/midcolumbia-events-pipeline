from src.category_intelligence import classify_event


def test_instructional_yoga_camps_are_classes() -> None:
    for event in (
        {"title": "Teen Yoga Trapeze Summer Camp", "description": "Each day includes yoga trapeze instruction with a certified instructor."},
        {"title": "Kids Yoga Day Camp", "description": "Kids will learn physical poses and breathing techniques."},
    ):
        assert classify_event(event).category == "Classes/Workshops"


def test_generic_camp_is_not_automatically_a_class() -> None:
    assert classify_event({"title": "Summer Camp"}).category is None


def test_structured_hands_on_making_is_a_class() -> None:
    for title in ("Sips & Ceramics", "Wine Blending Lab", "Pasta Making 101"):
        assert classify_event({"title": title}).category == "Classes/Workshops"


def test_explicit_beneficiary_or_proceeds_is_fundraiser() -> None:
    for title in ("Bookfair Benefitting the NICU", "Car Wash for a Cause", "Dinner - Proceeds Support Animal Rescue"):
        assert classify_event({"title": title}).category == "Fundraisers"


def test_nonprofit_mention_alone_is_not_fundraiser() -> None:
    assert classify_event({"title": "Humane Society Community Gathering"}).category != "Fundraisers"


def test_bingo_and_kareoke_lexical_rules() -> None:
    assert classify_event({"title": "August Botanical BINGO"}).category == "Trivia/Game Night"
    assert classify_event({"title": "Drag Queen Kareoke"}).category == "Karaoke/Open Mic"


def test_performance_evidence_required_at_mixed_use_venue() -> None:
    assert classify_event({"title": "The Night Hawks Concert", "venue": "Example Winery"}).category == "Music/Comedy"
    assert classify_event({"title": "The Night Hawks", "venue": "Example Winery"}).category is None


def test_explicit_social_event_phrases() -> None:
    for title in ("Family Night", "Clinic Grand Opening", "Back to School Bash", "Downtown Shop Crawl", "Plant Swap"):
        assert classify_event({"title": title}).category == "Events/Hangouts"
    assert classify_event({"title": "Community Update"}).category is None
