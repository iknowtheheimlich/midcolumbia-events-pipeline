from src.presentation_review import build_presentation_review


def test_builds_deduplicated_venue_and_host_review_items() -> None:
    events = [
        {
            "title": "Live Music",
            "venue": "Mystery Room",
            "city": "Richland",
            "source": "TestSource",
            "url": "https://example.org/1",
            "detected_host": "Mystery Band",
            "presentation_review_reasons": ["unresolved_host"],
        },
        {
            "title": "Another Show",
            "venue": "Mystery Room",
            "city": "Richland",
            "source": "OtherSource",
            "url": "https://example.org/2",
            "detected_host": "Mystery Band",
            "presentation_review_reasons": ["unresolved_host"],
        },
    ]

    items = build_presentation_review(events)

    assert [(item.kind, item.detected_name) for item in items] == [
        ("HOST", "Mystery Band"),
        ("VENUE", "Mystery Room"),
    ]


def test_resolved_venue_without_review_reason_is_not_queued() -> None:
    items = build_presentation_review(
        [
            {
                "title": "Event",
                "venue": "Known Venue",
                "venue_registry_name": "Known Venue",
                "source": "Test",
                "url": "https://example.org/event",
            }
        ]
    )

    assert items == []
