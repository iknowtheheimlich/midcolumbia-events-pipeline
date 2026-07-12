from datetime import date

from src.pipeline import PipelineResult
from tools.publish_reddit_live import _in_week, _weekly_editorial_events


def test_in_week_includes_start_and_excludes_end():
    start = date(2026, 7, 12)
    assert _in_week("2026-07-12", start, 7)
    assert _in_week("2026-07-18", start, 7)
    assert not _in_week("2026-07-19", start, 7)


def test_in_week_rejects_bad_dates():
    start = date(2026, 7, 12)
    assert not _in_week("", start, 7)
    assert not _in_week("not-a-date", start, 7)


def test_weekly_editorial_events_uses_pipeline_editorial_projection():
    pipeline = PipelineResult(
        deduplicated_publisher_ready_events=[
            {
                "title": "Inside Week",
                "venue": "Richland Library",
                "city": "Richland",
                "start_date": "2026-07-15",
                "url": "https://example.org/inside",
                "source": "TestSource",
                "geo_scope": "LOCAL",
                "content_kind": "EVENT",
            },
            {
                "title": "Outside Week",
                "venue": "Richland Library",
                "city": "Richland",
                "start_date": "2026-07-21",
                "url": "https://example.org/outside",
                "source": "TestSource",
                "geo_scope": "LOCAL",
                "content_kind": "EVENT",
            },
        ]
    )

    weekly = _weekly_editorial_events(pipeline, date(2026, 7, 12), 7)

    assert [event.title for event in weekly] == ["Inside Week"]
