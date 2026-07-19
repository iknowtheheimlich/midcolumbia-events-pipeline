import json
from pathlib import Path

from src.review_console import build_review_console, published_lookup


def test_published_lookup_uses_reddit_category_heading(tmp_path: Path) -> None:
    post = tmp_path / "post.txt"
    post.write_text(
        "## Food & Drink\n\nVisiting Winemaker at Solar Spirits | Solar Spirits, Richland | 6:30p\n",
        encoding="utf-8",
    )
    lookup = published_lookup([post])
    assert lookup["visiting winemaker at solar spirits"]["category"] == "Food & Drink"


def test_console_preloads_published_match_and_editorial_fields(tmp_path: Path) -> None:
    training = tmp_path / "Review_Training.json"
    training.write_text(
        json.dumps({
            "schema_version": 3,
            "record_count": 1,
            "records": [{
                "fingerprint": "abc123",
                "title": "Visiting Winemaker at Solar Spirits",
                "source": "VisitTriCities",
                "source_event_id": "1",
                "publication_url": "https://example.org",
                "publication_disposition": "REVIEW",
                "start_date": "2026-07-14",
                "start_time": "18:30",
                "venue": "Solar Spirits",
                "city": "Richland",
                "host": "Frichette Winery",
                "host_url": "https://frichettewinery.com",
                "description": "Wine tasting",
                "duplicate_sources": ["AllEvents"],
                "current_category": None,
                "category_confidence": 0.0,
                "category_reason": "no_category_rule_matched",
                "geographic_scope": "LOCAL",
                "editorial_reason": "missing_or_unknown_category",
                "intelligence": {},
                "correction": None,
            }],
        }),
        encoding="utf-8",
    )
    post = tmp_path / "post.txt"
    post.write_text(
        "## Food & Drink\n\nVisiting Winemaker at Solar Spirits | Solar Spirits, Richland | 6:30p\n",
        encoding="utf-8",
    )
    output = tmp_path / "Review_Console.html"
    build_review_console(training, output, published_paths=[post])
    text = output.read_text(encoding="utf-8")
    assert "Found in this week’s post" in text
    assert '"category": "Food & Drink"' in text
    assert "Host / publisher" in text
    assert "Review_Corrections.json" in text
