from src.host_registry import HostRecord, HostRegistry


def test_curated_host_url_replaces_source_guess() -> None:
    registry = HostRegistry(
        [HostRecord(name="The Knockoffs", website="https://theknockoffs.example/", aliases=("Knockoffs",))]
    )

    enriched = registry.enrich(
        {
            "title": "Live Music",
            "organization": "Knockoffs",
            "organization_url": "https://source.example/event",
        }
    )

    assert enriched["organization"] == "The Knockoffs"
    assert enriched["organization_url"] == "https://theknockoffs.example/"
    assert enriched["host_registry_name"] == "The Knockoffs"


def test_unresolved_detected_host_is_sent_to_review() -> None:
    enriched = HostRegistry().enrich(
        {"title": "Live Music", "performer": "Mystery Band"}
    )

    assert enriched["detected_host"] == "Mystery Band"
    assert enriched["presentation_review_reasons"] == ["unresolved_host"]


def test_host_website_precedes_event_calendar() -> None:
    record = HostRecord(
        name="Organizer",
        website="https://organizer.example/",
        event_calendar="https://organizer.example/events",
    )

    assert record.publication_url == "https://organizer.example/"
