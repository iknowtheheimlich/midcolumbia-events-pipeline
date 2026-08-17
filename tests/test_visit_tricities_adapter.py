from adapters.visit_tricities.adapter import normalize_hit


def _hit(**overrides):
    value = {"objectID": "1", "title": "Ordinary Event", "content": "An ordinary event.", "eventLocation": "Prosser", "address": ["Prosser", "Prosser, Washington 99350"], "partnerRegions": ["Prosser"], "startDate": 1787248800, "endDate": 1787270340, "uri": "/ordinary-event/"}
    value.update(overrides)
    return value


def test_recovers_corroborated_named_venue_before_city_fallback():
    event = normalize_hit(_hit(title="Sip & Shop Night Market at Desert Moon Winery", content="Join us at Desert Moon Winery for the night market.", website="https://www.desertmoonwinery.com/calendar-of-events"))
    assert event["venue"] == "Desert Moon Winery"


def test_does_not_infer_venue_from_arbitrary_title_suffix():
    event = normalize_hit(_hit(title="Ordinary Event at Imaginary Hall", content="Join us for an ordinary event.", website="https://example.com/event"))
    assert event["venue"] == "Prosser"
