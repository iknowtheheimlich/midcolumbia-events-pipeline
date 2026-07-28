import json
from pathlib import Path

import pytest

from src.publisher_editorial import EditorialEvent
from src.review_trainer import (
    build_review_training_records,
    load_corrections,
    review_fingerprint,
    write_review_training_artifact,
)


def event(**overrides) -> EditorialEvent:
    values = dict(
        title="Visiting Winemaker: Frichette Winery takes over Solar Spirits!",
        start_date="2026-07-14",
        end_date="2026-07-14",
        display_start_time="18:30",
        display_end_time=None,
        display_time="6:30p",
        display_venue="Solar Spirits",
        display_city="Richland",
        display_organization="Frichette Winery",
        publication_url="https://example.org/event",
        publication_disposition="REVIEW",
        editorial_reason="missing_or_unknown_category",
        publication_target="REVIEW",
        semantic_category=None,
        source="VisitTriCities",
        source_event_id="abc-123",
        venue_id="solar-place-id",
        venue_type="Distillery",
        geographic_scope="LOCAL",
        region="TRI_CITIES",
        location_type="VENUE",
        category=None,
        description="A visiting winemaker tasting event.",
        eventbrite_event_id=None,
        duplicate_sources=("VisitTriCities", "AllEvents"),
        duplicate_count=2,
        category_confidence=0.0,
        category_reason="no_category_rule_matched",
        canonical_title="Visiting Winemaker: Frichette Winery takes over Solar Spirits!",
        style_reason="unchanged",
        display_organization_url="https://frichettewinery.com",
        intelligence={"category": {"value": None, "confidence": 0.0, "reason": "no_category_rule_matched"}},
    )
    values.update(overrides)
    return EditorialEvent(**values)


def test_fingerprint_is_stable_and_ignores_list_position() -> None:
    first = event()
    second = event(duplicate_count=3, duplicate_sources=("VisitTriCities", "AllEvents", "TriCityVibe"))
    assert review_fingerprint(first) == review_fingerprint(second)


def test_training_records_are_deterministically_sorted() -> None:
    later = event(title="Zulu", canonical_title="Zulu", start_date="2026-07-18", source_event_id="2")
    earlier = event(title="Alpha", canonical_title="Alpha", start_date="2026-07-14", source_event_id="1")
    records = build_review_training_records([later, earlier])
    assert [record.title for record in records] == ["Alpha", "Zulu"]


def test_training_record_contains_full_editorial_context() -> None:
    record = build_review_training_records([event()])[0]
    assert record.publication_url == "https://example.org/event"
    assert record.publication_disposition == "REVIEW"
    assert record.editorial_reason == "missing_or_unknown_category"
    assert record.category_reason == "no_category_rule_matched"
    assert record.host == "Frichette Winery"
    assert record.host_url == "https://frichettewinery.com"
    assert record.description == "A visiting winemaker tasting event."
    assert record.duplicate_sources == ("VisitTriCities", "AllEvents")


def test_editorial_correction_attaches_by_fingerprint(tmp_path: Path) -> None:
    target = event()
    fingerprint = review_fingerprint(target)
    corrections_path = tmp_path / "corrections.json"
    corrections_path.write_text(
        json.dumps({"corrections": [{
            "fingerprint": fingerprint,
            "action": "EDITORIAL",
            "decision": "INCLUDE",
            "corrected_title": "Visiting Winemaker at Solar Spirits",
            "corrected_venue": "Solar Spirits",
            "corrected_host": "Frichette Winery",
            "correct_category": "Food & Drink",
        }]}),
        encoding="utf-8",
    )
    output = tmp_path / "review.json"
    records = write_review_training_artifact([target], output, corrections_path=corrections_path)
    assert records[0].correction["action"] == "EDITORIAL"
    assert records[0].correction["correct_category"] == "Food & Drink"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 3
    assert payload["record_count"] == 1
    assert payload["records"][0]["host"] == "Frichette Winery"


def test_invalid_or_duplicate_corrections_fail_loudly(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"corrections": [{"fingerprint": "abc", "action": "MAGIC"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_corrections(invalid)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        json.dumps({"corrections": [
            {"fingerprint": "abc", "action": "CATEGORY"},
            {"fingerprint": "abc", "action": "SUPPRESS"},
        ]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_corrections(duplicate)
