from src.category_intelligence import classify_event, enrich_event_category
from src.pipeline import SourceBatch, run_pipeline


def event(**overrides):
    values = {
        "title": "Untitled Event",
        "venue": "Test Venue",
        "city": "Richland",
        "start_date": "2026-07-15",
        "url": "https://example.org/event",
        "source": "TestSource",
        "geo_scope": "LOCAL",
        "content_kind": "EVENT",
    }
    values.update(overrides)
    return values


def test_preserves_existing_semantic_category() -> None:
    decision = classify_event(event(category="Sports", title="Mystery"))
    assert decision.category == "Sports"
    assert decision.confidence == 1.0
    assert decision.reason == "existing_semantic_category"


def test_classifies_storytime_as_community_program() -> None:
    decision = classify_event(event(title="Baby Storytime With Ms. Amy"))
    assert decision.category == "Community Programs"
    assert decision.confidence >= 0.9
    assert decision.reason == "keyword=storytime"


def test_classifies_open_mic_before_generic_music() -> None:
    decision = classify_event(event(title="Live Music Open Mic at Emerald"))
    assert decision.category == "Karaoke/Open Mic"
    assert decision.reason == "keyword=open mic"


def test_classifies_source_category_without_copying_source_vocabulary() -> None:
    decision = classify_event(event(title="Unknown", source_category="Food & Drink"))
    assert decision.category == "Restaurants/Bars/Wineries"
    assert decision.reason == "source_category=Food & Drink"


def test_unmatched_event_stays_unclassified_and_explained() -> None:
    decision = classify_event(event(title="An Extremely Ambiguous Thing"))
    assert decision.category is None
    assert decision.confidence == 0.0
    assert decision.reason == "no_category_rule_matched"


def test_enrichment_is_additive_and_does_not_mutate_input() -> None:
    original = event(title="Tri-City Dust Devils Game")
    enriched = enrich_event_category(original)
    assert "category" not in original
    assert enriched["category"] == "Sports"
    assert enriched["category_confidence"] > 0
    assert enriched["category_reason"].startswith("keyword=")


def test_pipeline_category_enrichment_is_opt_in_for_backwards_compatibility() -> None:
    batch = SourceBatch("TestSource", [event(title="Open Mic")])
    legacy = run_pipeline([batch])
    enriched = run_pipeline([batch], enrich_categories=True)
    assert legacy.all_events[0].get("category") is None
    assert enriched.all_events[0]["category"] == "Karaoke/Open Mic"


def test_category_explanation_survives_projection_and_editorial_layers() -> None:
    pipeline = run_pipeline(
        [SourceBatch("TestSource", [event(title="Open Mic")])],
        enrich_categories=True,
    )
    projected = pipeline.publisher_projection[0]
    editorial = pipeline.editorial_projection[0]
    assert projected.category_reason == "keyword=open mic"
    assert projected.category_confidence == 0.99
    assert editorial.category_reason == "keyword=open mic"
    assert editorial.semantic_category == "Karaoke/Open Mic"
    assert editorial.publication_target == "MAIN"
