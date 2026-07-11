from adapters.eventbrite.bridge import bridge_items, extract_event_id, is_eventbrite_url


def test_eventbrite_url_detection() -> None:
    assert is_eventbrite_url("https://www.eventbrite.com/e/sample-event-123456789012")
    assert is_eventbrite_url("https://eventbrite.com/e/sample-event-123456789012")
    assert not is_eventbrite_url("https://example.com/eventbrite")
    assert not is_eventbrite_url(None)


def test_eventbrite_event_id_extraction() -> None:
    assert extract_event_id("https://www.eventbrite.com/e/sample-event-123456789012") == "123456789012"
    assert extract_event_id("https://www.eventbrite.com/e/no-numeric-id") is None


def test_bridge_items_deduplicates_by_event_id() -> None:
    events = [
        {
            "title": "Local Event",
            "start_date": "2026-07-18",
            "start_time": "18:00",
            "venue": "Test Hall",
            "city": "Richland",
            "source": "VisitTriCities",
            "url": "https://local.example/event",
            "external_url": "https://www.eventbrite.com/e/local-event-123456789012",
        },
        {
            "title": "Local Event Repost",
            "start_date": "2026-07-18",
            "source": "TriCityVibe",
            "url": "https://www.eventbrite.com/e/another-slug-123456789012?aff=oddtdtcreator",
        },
    ]

    items = bridge_items(events)

    assert len(items) == 1
    assert items[0].event_id == "123456789012"
    assert items[0].source == "VisitTriCities"
