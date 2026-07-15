from src.category_intelligence import enrich_event_category
from src.classification_observability import (
    attach_classification_observability,
    confidence_band,
    evidence_from_reason,
    sort_for_category_review,
)


def test_reason_maps_to_structured_evidence():
    assert evidence_from_reason("organizer_hint=WSU Tri-Cities;strength=high") == ["OrganizerHint"]
    assert evidence_from_reason("title_rule=fundraiser") == ["TitleRule"]


def test_confidence_bands_are_deterministic():
    assert confidence_band(0.95) == "high"
    assert confidence_band(0.80) == "medium"
    assert confidence_band(0.40) == "low"
    assert confidence_band(0.0) == "none"


def test_observability_does_not_change_category():
    event = {
        "title": "Existing",
        "category": "Sports",
        "category_confidence": 0.61,
        "category_reason": "description_rule=sports",
    }
    observed = attach_classification_observability(event)
    assert observed["category"] == "Sports"
    assert observed["category_confidence"] == 0.61
    assert observed["category_evidence"] == ["DescriptionRule"]
    assert observed["category_needs_review"] is True


def test_enrichment_attaches_evidence_without_changing_decision():
    event = enrich_event_category({"title": "Open Mic at Fiction"})
    assert event["category"] == "Karaoke/Open Mic"
    assert event["category_confidence"] == 0.99
    assert event["category_evidence"] == ["TitleRule"]
    assert event["category_confidence_band"] == "high"


def test_unmatched_event_is_observable():
    event = enrich_event_category({"title": "Completely Ambiguous Thing"})
    assert event.get("category") is None
    assert event["category_confidence"] == 0.0
    assert event["category_evidence"] == ["NoMatch"]
    assert event["category_needs_review"] is False


def test_review_sort_places_lowest_confidence_first():
    events = [
        {"title": "High", "category": "Sports", "category_confidence": 0.95, "category_reason": "title_rule=sports"},
        {"title": "Low", "category": "Sports", "category_confidence": 0.41, "category_reason": "description_rule=sports"},
        {"title": "Medium", "category": "Sports", "category_confidence": 0.80, "category_reason": "source_category=sports"},
    ]
    ordered = sort_for_category_review(events)
    assert [event["title"] for event in ordered] == ["Low", "Medium", "High"]
