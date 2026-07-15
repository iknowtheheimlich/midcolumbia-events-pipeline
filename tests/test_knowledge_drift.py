from src.knowledge_drift import detect_knowledge_drift


def _events(entity_field, entity_name, categories):
    rows = []
    day = 1
    for category in categories:
        rows.append({entity_field: entity_name, "category": category, "start_date": f"2026-07-{day:02d}"})
        day += 1
    return rows


def test_stable_venue_hint_remains_stable():
    events = _events("venue", "Art YOUR Way", ["Classes/Workshops"] * 9 + ["Fundraisers"])
    results = detect_knowledge_drift(events, venue_hints={"Art YOUR Way": {"category_hint": "Classes/Workshops"}})
    assert results[0].status == "STABLE"
    assert results[0].expected_percent == 0.9


def test_venue_hint_watch_threshold():
    events = _events("venue", "CBC Planetarium", ["Lectures/Talks"] * 7 + ["Art/Theater"] * 3)
    result = detect_knowledge_drift(events, venue_hints={"CBC Planetarium": {"category_hint": "Lectures/Talks"}})[0]
    assert result.status == "WATCH"
    assert result.recommendation == "monitor"


def test_venue_hint_drift_threshold():
    events = _events("venue", "CBC Planetarium", ["Lectures/Talks"] * 5 + ["Art/Theater"] * 5)
    result = detect_knowledge_drift(events, venue_hints={"CBC Planetarium": {"category_hint": "Lectures/Talks"}})[0]
    assert result.status == "DRIFT"
    assert result.recommendation == "review_hint"


def test_insufficient_recent_evidence_does_not_flag_drift():
    events = _events("venue", "Art YOUR Way", ["Fundraisers"] * 3)
    result = detect_knowledge_drift(events, venue_hints={"Art YOUR Way": {"category_hint": "Classes/Workshops"}})[0]
    assert result.status == "INSUFFICIENT"
    assert result.recommendation == "keep"


def test_organizer_drift_travels_across_venues():
    events = []
    for index, category in enumerate(["Classes/Workshops"] * 4 + ["Community Programs"] * 6, start=1):
        events.append({
            "organization": "Master Gardeners",
            "venue": "Richland Library" if index % 2 else "REACH Museum",
            "category": category,
            "start_date": f"2026-07-{index:02d}",
        })
    result = detect_knowledge_drift(events, organizer_hints={"Master Gardeners": {"category_hint": "Classes/Workshops"}})[0]
    assert result.entity_type == "organizer"
    assert result.status == "DRIFT"
    assert result.dominant_category == "Community Programs"


def test_recent_limit_ignores_old_behavior():
    events = _events("venue", "Art YOUR Way", ["Classes/Workshops"] * 20 + ["Fundraisers"] * 10)
    result = detect_knowledge_drift(
        events,
        venue_hints={"Art YOUR Way": {"category_hint": "Classes/Workshops"}},
        recent_limit=10,
    )[0]
    assert result.recent_events == 10
    assert result.status == "DRIFT"
