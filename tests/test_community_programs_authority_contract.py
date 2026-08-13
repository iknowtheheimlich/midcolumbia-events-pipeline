from src.category_intelligence import classify_event, community_programs_authority_eligible


def test_public_library_host_qualifies_for_community_programs() -> None:
    event = {"title": "Storytime", "organizer": "Mid-Columbia Libraries", "venue": "Commercial Plaza"}
    decision = classify_event(event)
    assert decision.category == "Community Programs"
    assert community_programs_authority_eligible(event)


def test_museum_and_municipal_and_community_center_hosts_qualify() -> None:
    for host in ("Franklin County Historical Museum", "City of Pasco Parks and Recreation", "Richland Community Center"):
        decision = classify_event({"title": "Teen Program", "host": host, "venue": "Offsite Room"})
        assert decision.category == "Community Programs", host


def test_private_organizer_at_library_venue_does_not_qualify() -> None:
    event = {"title": "Meditation Gathering", "organizer": "Private Wellness LLC", "venue": "Richland Public Library", "venue_type": "library"}
    decision = classify_event(event)
    assert decision.category == "Events/Hangouts"
    assert decision.reason == "title_rule=social_event"


def test_failed_community_gate_continues_normal_semantic_classification() -> None:
    event = {"title": "Live Music Teen Program", "organizer": "Commercial Events Inc.", "venue": "Richland Public Library", "venue_type": "library"}
    decision = classify_event(event)
    assert decision.category == "Music/Comedy"
    assert decision.reason == "title_rule=explicit_live_performance"


def test_private_wellness_event_is_not_community_programs() -> None:
    decision = classify_event({"title": "Recovery Dharma", "description": "Guided meditation", "host": "Lifted Lotus Yoga Collective", "venue": "Lifted Lotus Yoga Collective"})
    assert decision.category is None
    assert decision.reason == "no_category_rule_matched"


def test_library_venue_without_distinct_organizer_may_supply_authority() -> None:
    decision = classify_event({"title": "Book Club", "venue": "Richland Public Library", "venue_type": "library"})
    assert decision.category == "Community Programs"


def test_school_venue_alone_no_longer_qualifies() -> None:
    decision = classify_event({"title": "Teen Program", "venue": "Private Academy", "venue_type": "school"})
    assert decision.category is None


def test_existing_community_category_is_gated_but_not_rejected() -> None:
    decision = classify_event({"title": "Neighborhood Gathering", "category": "Community Programs", "organizer": "Commercial Events LLC", "venue": "Downtown Hall"})
    assert decision.category == "Events/Hangouts"
    assert decision.reason == "title_rule=social_event"


def test_first_party_library_source_qualifies_at_offsite_venue() -> None:
    decision = classify_event({"title": "Rock Decorating with Sharpies", "source": "RichlandLibrary", "venue": "Columbia Point Marina Park", "category": "Community Programs"})
    assert decision.category == "Community Programs"


def test_explicit_library_sponsorship_in_description_qualifies() -> None:
    decision = classify_event({"title": "Adult Book Club", "description": "Join the library's monthly book club for discussion.", "venue": "235 E Gladys Ave", "category": "Community Programs"})
    assert decision.category == "Community Programs"


def test_superseded_private_examples_do_not_qualify() -> None:
    cases = (
        {"title": "Barnes & Noble Presents Children's Story-time!", "organizer": "Barnes & Noble", "venue": "Columbia Center Mall"},
        {"title": "Recovery Dharma", "organizer": "Lifted Lotus Yoga Collective", "venue": "Richland Public Library"},
        {"title": "Women's Retreat", "organizer": "Private Wellness LLC", "venue": "Hansen Park"},
        {"title": "Children's Storytime", "venue": "Commercial Plaza"},
    )
    for event in cases:
        assert classify_event(event).category != "Community Programs"
