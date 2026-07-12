from datetime import date

from tools.publish_reddit_live import _in_week


def test_in_week_includes_start_and_excludes_end():
    start = date(2026, 7, 12)
    assert _in_week("2026-07-12", start, 7)
    assert _in_week("2026-07-18", start, 7)
    assert not _in_week("2026-07-19", start, 7)


def test_in_week_rejects_bad_dates():
    start = date(2026, 7, 12)
    assert not _in_week("", start, 7)
    assert not _in_week("not-a-date", start, 7)
