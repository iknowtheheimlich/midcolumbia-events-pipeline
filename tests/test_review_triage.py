import json

from src.review_triage import build_review_triage, classify_review_record
from tools.build_review_triage import write_review_triage


def test_category_only_review_is_editorial_work() -> None:
    item = classify_review_record(
        {
            "fingerprint": "abc",
            "title": "Unclassified Event",
            "source": "AllEvents",
            "editorial_reason": "missing_or_unknown_category",
        }
    )

    assert item.severity == "EDITORIAL_REVIEW"
    assert item.entity_type == "CATEGORY"


def test_geographic_and_missing_city_reviews_are_publication_blockers() -> None:
    geographic = classify_review_record(
        {"title": "Regional Event", "editorial_reason": "geographic_review"}
    )
    missing_city = classify_review_record(
        {"title": "Placeless Event", "editorial_reason": "missing_city"}
    )

    assert geographic.severity == "PUBLICATION_BLOCKER"
    assert geographic.entity_type == "GEOGRAPHY"
    assert missing_city.severity == "PUBLICATION_BLOCKER"
    assert missing_city.entity_type == "GEOGRAPHY"


def test_builds_reason_entity_and_source_counts() -> None:
    triage = build_review_triage(
        [
            {
                "title": "Category A",
                "source": "AllEvents",
                "editorial_reason": "missing_or_unknown_category",
            },
            {
                "title": "Category B",
                "source": "AllEvents",
                "editorial_reason": "missing_or_unknown_category",
            },
            {
                "title": "Regional",
                "source": "TriCityVibe",
                "editorial_reason": "geographic_review",
            },
        ]
    )

    assert triage["record_count"] == 3
    assert triage["editorial_reviews"] == 2
    assert triage["publication_blockers"] == 1
    assert triage["by_reason"] == {
        "geographic_review": 1,
        "missing_or_unknown_category": 2,
    }
    assert triage["by_entity_type"] == {"CATEGORY": 2, "GEOGRAPHY": 1}
    assert triage["by_source"] == {"AllEvents": 2, "TriCityVibe": 1}


def test_writes_actionable_json_csv_and_text_artifacts(tmp_path) -> None:
    triage = build_review_triage(
        [
            {
                "fingerprint": "abc",
                "title": "Regional Event",
                "source": "AllEvents",
                "start_date": "2026-07-20",
                "venue": "Venue",
                "city": "Prosser",
                "publication_url": "https://example.com/event",
                "editorial_reason": "geographic_review",
            }
        ]
    )

    paths = write_review_triage(triage, tmp_path)

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    report = paths["report"].read_text(encoding="utf-8")
    csv_text = paths["csv"].read_text(encoding="utf-8")
    assert payload["publication_blockers"] == 1
    assert "PUBLICATION_BLOCKER" in report
    assert "Regional Event" in report
    assert "severity,entity_type,reason" in csv_text
