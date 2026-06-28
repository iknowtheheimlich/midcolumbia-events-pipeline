import tempfile
import unittest
from pathlib import Path

from cargo_harvester.core import dedupe_events, write_events_csv, write_debug_json
from cargo_harvester.models import EventRecord


class CoreTests(unittest.TestCase):
    def test_dedupe_events_removes_duplicate_keys(self):
        first = EventRecord(event_name="A", date_raw="2026-07-04", source_url="https://example.com/a").finalize()
        second = EventRecord(event_name="A", date_raw="2026-07-04", source_url="https://example.com/a").finalize()

        deduped = dedupe_events([first, second])

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].event_name, "A")

    def test_write_events_csv_creates_file(self):
        event = EventRecord(event_name="A", date_raw="2026-07-04", source_url="https://example.com/a").finalize()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            write_events_csv([event], path)
            text = path.read_text(encoding="utf-8")

        self.assertIn("Event Name", text)
        self.assertIn("A", text)

    def test_write_debug_json_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debug.json"
            write_debug_json([{"name": "A"}], path)
            text = path.read_text(encoding="utf-8")

        self.assertIn('"name"', text)
        self.assertIn('"A"', text)


if __name__ == "__main__":
    unittest.main()
