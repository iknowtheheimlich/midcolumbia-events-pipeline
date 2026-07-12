from pathlib import Path

import pytest

from src.publisher_audit import (
    default_audit_path,
    render_publisher_audit,
    write_publisher_audit,
)
from src.publisher_editorial import EditorialEvent


def editorial_event(**overrides: object) -> EditorialEvent:
    values = {
        "title": "Event",
        "start_date": "2026-07-12",
        "end_date": None,
        "display_start_time": "18:00",
        "display_end_time": None,
        "display_time": "6p",
        "display_venue": "Venue",
        "display_city": "Richland",
        "display_organization": None,
        "publication_url": "https://example.com/event",
        "publication_disposition": "AUTO_PUBLISH",
        "editorial_reason": None,
        "publication_target": "MAIN",
        "semantic_category": "Events/Hangouts",
        "source": "TestSource",
        "source_event_id": "event-1",
        "venue_id": "place-1",
        "venue_type": "Venue",
        "geographic_scope": "LOCAL",
        "region": "TRI_CITIES",
        "location_type": "VENUE",
        "category": "Events/Hangouts",
        "description": None,
        "eventbrite_event_id": None,
        "duplicate_sources": (),
        "duplicate_count": 1,
    }
    values.update(overrides)
    return EditorialEvent(**values)


def test_audit_reports_targets_categories_and_review_reasons() -> None:
    report = render_publisher_audit(
        [
            editorial_event(title="Main", publication_target="MAIN"),
            editorial_event(
                title="Community",
                publication_target="COMMUNITY",
                semantic_category="Community Programs",
                category="Community Programs",
            ),
            editorial_event(
                title="Review",
                publication_disposition="REVIEW",
                publication_target="REVIEW",
                semantic_category=None,
                category=None,
                editorial_reason="missing_or_unknown_category",
            ),
        ],
        category_order=("Events/Hangouts", "Community Programs"),
    )

    assert "Weekly editorial events: 3" in report
    assert "  MAIN: 1" in report
    assert "  COMMUNITY: 1" in report
    assert "  UNCLASSIFIED: 1" in report
    assert "  missing_or_unknown_category: 1" in report


def test_write_audit_rejects_fixture_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="separate from fixtures"):
        write_publisher_audit(
            [],
            tmp_path / "fixtures" / "audit.txt",
            category_order=(),
        )


def test_default_audit_path_is_stable() -> None:
    assert default_audit_path() == Path("artifacts/reddit/Publisher_Audit.txt")
