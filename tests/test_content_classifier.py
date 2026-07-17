from src.content_classifier import classify_content, screen_events
from src.pipeline import SourceBatch, run_pipeline


def test_navigation_and_pagination_titles_are_rejected():
    for title in ("Login", "Current page 1", "Page 7", "Next page ››"):
        result = classify_content({"title": title})
        assert result.publishable is False


def test_known_document_job_and_admin_pages_are_rejected():
    expected = {
        "All Library Policies": "DOCUMENT",
        "Employment Opportunities": "JOB",
        "Volunteer": "PAGE",
        "Intranet": "PAGE",
    }
    for title, kind in expected.items():
        result = classify_content({"title": title})
        assert result.publishable is False
        assert result.kind == kind


def test_phone_number_only_titles_are_rejected_as_contact_chrome():
    for title in ("(509) 783-7878", "509-783-7878", "+1 509 783 7878"):
        result = classify_content({"title": title})
        assert result.publishable is False
        assert result.kind == "CONTACT"
        assert result.reason == "phone_number_title"


def test_real_event_titles_are_not_overclassified():
    for title in (
        "Volunteer Appreciation Picnic",
        "Careers in Science Night",
        "Page Turner Book Club",
        "Login to the Matrix Trivia",
        "Call 509-783-7878 for Storytime Registration",
    ):
        result = classify_content({"title": title})
        assert result.publishable is True
        assert result.kind == "EVENT"


def test_screen_events_preserves_rejected_items_for_audit():
    accepted, rejected = screen_events(
        [
            {"title": "LEGO Club"},
            {"title": "Page 3", "source": "MidColumbiaLibraries"},
        ]
    )
    assert [event["title"] for event in accepted] == ["LEGO Club"]
    assert rejected[0]["content_kind"] == "NAVIGATION"
    assert rejected[0]["content_rejection_reason"] == "pagination_title"


def test_pipeline_content_screening_is_optional_and_auditable():
    batch = SourceBatch(
        source_name="TestSource",
        events=[
            {"title": "LEGO Club", "start_date": "2026-07-12"},
            {"title": "Login", "start_date": "2026-07-12"},
        ],
    )

    plain = run_pipeline([batch])
    screened = run_pipeline([batch], screen_content=True)

    assert len(plain.publisher_ready_events) == 2
    assert len(screened.publisher_ready_events) == 1
    assert len(screened.content_rejected_events) == 1
    assert screened.content_rejected_events[0]["title"] == "Login"
