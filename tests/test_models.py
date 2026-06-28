import unittest

from cargo_harvester.models import EventRecord, is_fatal


class EventRecordTests(unittest.TestCase):
    def test_finalize_marks_clean_event(self):
        event = EventRecord(
            event_name="Test Event",
            date_raw="2026-07-04",
            start_time="9:00 AM",
            venue="Test Park",
            city="Kennewick",
            source_url="https://example.com/event",
            image_url="https://example.com/image.jpg",
        ).finalize()

        self.assertEqual(event.needs_review, "No")
        self.assertEqual(event.review_notes, "")
        self.assertFalse(is_fatal(event))
        self.assertTrue(event.dedupe_key)

    def test_finalize_marks_nonfatal_missing_time_venue_image(self):
        event = EventRecord(
            event_name="Test Event",
            date_raw="2026-07-04",
            city="Kennewick",
            source_url="https://example.com/event",
        ).finalize()

        self.assertEqual(event.needs_review, "Yes")
        self.assertIn("Missing start time", event.review_notes)
        self.assertIn("Missing venue", event.review_notes)
        self.assertIn("Missing image URL", event.review_notes)
        self.assertFalse(is_fatal(event))

    def test_finalize_marks_fatal_missing_identity_fields(self):
        event = EventRecord().finalize()

        self.assertEqual(event.needs_review, "Yes")
        self.assertIn("Missing event name", event.review_notes)
        self.assertIn("Missing date", event.review_notes)
        self.assertIn("Missing source URL", event.review_notes)
        self.assertTrue(is_fatal(event))


if __name__ == "__main__":
    unittest.main()
