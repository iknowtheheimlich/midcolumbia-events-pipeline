import pytest

from src.category_intelligence import classify_event
from src.publishing_contract import PublishingProfile


@pytest.mark.parametrize(
    "event",
    [
        {"title": "Beginning Watercolor Class"},
        {"title": "Sourdough Workshop"},
        {"title": "CPR Skills Clinic"},
        {"title": "Teen Yoga Trapeze Summer Camp", "description": "Guided yoga instruction."},
        {"title": "Pasta Making 101"},
    ],
    ids=("class", "workshop", "clinic", "instructional-fitness", "structured-making"),
)
def test_representative_classes_and_workshops_route_main(event):
    decision = classify_event(event)
    profile = PublishingProfile.load()

    assert decision.category == "Classes/Workshops"
    assert profile.publication_target(decision.category) == "MAIN"


def test_explicit_event_target_still_overrides_classes_default():
    profile = PublishingProfile.load()

    assert profile.publication_target("Classes/Workshops", "COMMUNITY") == "COMMUNITY"
