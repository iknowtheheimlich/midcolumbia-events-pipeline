from pathlib import Path

from src.historical_corpus import build_historical_corpus, write_historical_corpus


def _row(**overrides):
    row = {
        "Event Name": "Live Music with The Band",
        "Date": "07/15/2026",
        "Time, Price, Notes": "6p",
        "Venue Reddit Combo": "[The Venue](https://venue.example/?utm_source=test)",
        "🌆 Ultimate Venues": "The Venue (https://app.notion.com/p/venue)",
        "Host Reddit Combo": "[The Host](https://host.example/?fbclid=abc)",
        "Host": "The Host (https://app.notion.com/p/host)",
        "Generated From": "Weekly Music (https://app.notion.com/p/template)",
    }
    row.update(overrides)
    return row


def test_builds_curated_entities_and_artist_candidates() -> None:
    result = build_historical_corpus([_row(), _row(Date="07/22/2026")])

    assert result.row_count == 2
    assert result.venues[0]["canonical_name"] == "The Venue"
    assert result.venues[0]["website"] == "https://venue.example/"
    assert result.venues[0]["occurrences"] == 2
    assert result.venues[0]["first_seen"] == "2026-07-15"
    assert result.venues[0]["last_seen"] == "2026-07-22"
    assert result.hosts[0]["website"] == "https://host.example/"
    assert result.artist_candidates[0]["candidate_name"] == "The Band"
    assert result.artist_candidates[0]["needs_review"] is True


def test_learns_recurring_pattern_distribution() -> None:
    result = build_historical_corpus(
        [
            _row(Date="07/15/2026", **{"Time, Price, Notes": "6p"}),
            _row(Date="07/22/2026", **{"Time, Price, Notes": "6p"}),
            _row(Date="07/29/2026", **{"Time, Price, Notes": "7p"}),
        ]
    )

    pattern = result.recurring_patterns[0]
    assert pattern["family"] == "Weekly Music"
    assert pattern["occurrences"] == 3
    assert pattern["typical_weekday"] == "Wednesday"
    assert pattern["typical_time"] == "6p"
    assert pattern["typical_venue"] == "The Venue"
    assert 0.7 <= pattern["confidence"] <= 1.0


def test_writes_separate_knowledge_artifacts(tmp_path: Path) -> None:
    result = build_historical_corpus([_row()])
    paths = write_historical_corpus(result, tmp_path)

    assert set(paths) == {"venues", "hosts", "artist_candidates", "recurring_patterns", "summary"}
    assert all(path.exists() for path in paths.values())
    assert '"historical_rows": 1' in paths["summary"].read_text(encoding="utf-8")
