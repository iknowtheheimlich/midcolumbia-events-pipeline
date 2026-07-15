import json

from src.corpus_health import analyze_corpus_health, render_corpus_health
from tools.finalize_weekly_run import finalize_weekly_run


def test_corpus_health_counts_dimensions_and_missing_fields():
    health = analyze_corpus_health([
        {"category": "Sports", "source": "A", "venue": "Stadium", "start_date": "2026-07-01"},
        {"category": "Sports", "source": "A", "organization": "Team", "start_date": "2026-07-02"},
        {"category": "Music/Comedy", "source": "B", "venue": "Club"},
    ])
    assert health.total_events == 3
    assert health.distinct_sources == 2
    assert health.distinct_categories == 2
    assert health.distinct_venues == 2
    assert health.distinct_organizers == 1
    assert health.missing_venue == 1
    assert health.missing_date == 1
    assert health.category_distribution["Sports"] == 2


def test_health_report_is_readable():
    report = render_corpus_health(analyze_corpus_health([]))
    assert "Attempt 78 Corpus Health" in report
    assert "Total events: 0" in report
    assert "CATEGORY DISTRIBUTION" in report


def test_weekly_finalizer_updates_history_and_health(tmp_path):
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps([
        {"event_id": "one", "title": "Game", "category": "Sports", "source": "Test", "start_date": "2026-07-01", "venue": "Stadium"},
        {"event_id": "two", "title": "Unknown"},
    ]), encoding="utf-8")
    history = tmp_path / "history.jsonl"
    artifacts = tmp_path / "artifacts"

    result = finalize_weekly_run(input_path, history_path=history, artifacts_dir=artifacts, run_reports=False)

    assert result["inserted"] == 1
    assert result["skipped_unclassified"] == 1
    assert result["total"] == 1
    assert history.exists()
    health = json.loads((artifacts / "corpus_health.json").read_text(encoding="utf-8"))
    assert health["total_events"] == 1
    assert (artifacts / "corpus_health_report.txt").exists()


def test_weekly_finalizer_is_idempotent(tmp_path):
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps([
        {"event_id": "one", "title": "Game", "category": "Sports", "source": "Test", "start_date": "2026-07-01"}
    ]), encoding="utf-8")
    history = tmp_path / "history.jsonl"
    artifacts = tmp_path / "artifacts"

    first = finalize_weekly_run(input_path, history_path=history, artifacts_dir=artifacts, run_reports=False)
    second = finalize_weekly_run(input_path, history_path=history, artifacts_dir=artifacts, run_reports=False)

    assert first["inserted"] == 1
    assert second["inserted"] == 0
    assert second["updated"] == 0
    assert second["total"] == 1
