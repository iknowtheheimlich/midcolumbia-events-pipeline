from pathlib import Path

import pytest

from src.publishing_contract import (
    PublishingProfile,
    format_compact_range,
    format_compact_time,
)


def test_default_profile_loads_exact_category_vocabulary():
    profile = PublishingProfile.load(Path("config/reddit_publishing_profile.json"))

    assert profile.category_order[0] == "Events/Hangouts"
    assert profile.category_order[-1] == "Faith Based"
    assert len(profile.category_order) == 16


def test_profile_routes_categories_to_separate_posts():
    profile = PublishingProfile.load()

    assert profile.publication_target("Music/Comedy") == "MAIN"
    assert profile.publication_target("Community Programs") == "COMMUNITY"
    assert profile.publication_target(None) == "REVIEW"


def test_explicit_publication_target_overrides_category_default():
    profile = PublishingProfile.load()

    assert profile.publication_target("Community Programs", "MAIN") == "MAIN"
    assert profile.publication_target("Music/Comedy", "BOTH") == "BOTH"
    assert profile.publication_target("Music/Comedy", "nonsense") == "REVIEW"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00:00", "12a"),
        ("09:00", "9a"),
        ("10:30", "10:30a"),
        ("13:00", "1p"),
        ("17:45", "5:45p"),
        (None, None),
    ],
)
def test_compact_time_grammar(value, expected):
    assert format_compact_time(value) == expected


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ("17:00", "18:00", "5-6p"),
        ("10:30", "11:00", "10:30-11a"),
        ("11:00", "13:00", "11a-1p"),
        ("17:00", None, "5p"),
    ],
)
def test_compact_range_grammar(start, end, expected):
    assert format_compact_range(start, end) == expected


def test_profile_rejects_duplicate_category_assignments():
    with pytest.raises(ValueError, match="multiple publication targets"):
        PublishingProfile.from_dict(
            {
                "category_order": ["A"],
                "publication_targets": {"MAIN": ["A"], "COMMUNITY": ["A"]},
            }
        )
