import unittest

from cargo_harvester.models import EventRecord
from cargo_harvester.reddit import build_reddit_weekly_draft, include_in_reddit


class RedditTests(unittest.TestCase):
    def test_include_in_reddit_rejects_fatal_event(self):
        event = EventRecord().finalize()
        self.assertFalse(include_in_reddit(event))

    def test_reddit_draft_contains_event_link(self):
        event = EventRecord(
            event_name="Farmers Market",
            date_raw="2026-07-04",
            start_time="9:00 AM",
            venue="Columbia Park",
            city="Kennewick",
            source_url="https://example.com/farmers-market",
        ).finalize()

        draft = build_reddit_weekly_draft([event])

        self.assertIn("# Tri-Cities Events", draft)
        self.assertIn("## 2026-07-04", draft)
        self.assertIn("[Farmers Market](https://example.com/farmers-market)", draft)
        self.assertIn("Columbia Park, Kennewick | 9:00 AM", draft)

    def test_missing_time_becomes_time_tba(self):
        event = EventRecord(
            event_name="Farmers Market",
            date_raw="2026-07-04",
            venue="Columbia Park",
            city="Kennewick",
            source_url="https://example.com/farmers-market",
        ).finalize()

        draft = build_reddit_weekly_draft([event])

        self.assertIn("Time TBA", draft)


if __name__ == "__main__":
    unittest.main()
