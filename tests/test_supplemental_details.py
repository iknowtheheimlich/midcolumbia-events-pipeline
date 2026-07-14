from datetime import date

from src.supplemental_detail_audit import build_supplemental_detail_rows, render_supplemental_detail_audit
from src.supplemental_details import enrich_event_supplemental_details, extract_cost, extract_schedule_items


def test_extracts_free_cost():
    assert extract_cost("Admission is free for everyone.") == "Free"


def test_extracts_numeric_cost():
    assert extract_cost("Tickets: $15 in advance.") == "$15"


def test_existing_cost_remains_authoritative():
    event = enrich_event_supplemental_details({"cost": "$20", "description": "Tickets are $15."})
    assert event["cost"] == "$20"
    assert "cost_source" not in event


def test_extracts_labeled_schedule_assignments():
    items = extract_schedule_items("Doors open 6:00 PM. Opening act 7 PM. Headliner 8:30 PM.")
    assert [(item["time"], item["label"]) for item in items] == [
        ("6:00 PM", "Doors open"),
        ("7 PM", "Opening act"),
        ("8:30 PM", "Headliner"),
    ]


def test_does_not_promote_bare_time_as_schedule_item():
    assert extract_schedule_items("7:00 PM") == []


def test_recovery_does_not_change_canonical_event_time():
    event = enrich_event_supplemental_details(
        {
            "start_time": "18:00",
            "end_time": "21:00",
            "description": "Doors open 5:30 PM. Music starts 6:30 PM.",
        }
    )
    assert event["start_time"] == "18:00"
    assert event["end_time"] == "21:00"
    assert len(event["schedule_items"]) == 2


def test_weekly_audit_filters_and_surfaces_recovered_details():
    rows = build_supplemental_detail_rows(
        [
            {
                "title": "Concert",
                "start_date": "2026-07-14",
                "venue": "Park",
                "source": "AllEvents",
                "url": "https://example.com/concert",
                "description": "Free admission. Doors open 6 PM. Band begins 7 PM.",
            },
            {
                "title": "Later Event",
                "start_date": "2026-07-25",
                "description": "Tickets $10.",
            },
        ],
        week_start=date(2026, 7, 13),
    )
    assert len(rows) == 1
    assert rows[0]["cost"] == "Free"
    assert len(rows[0]["schedule_items"]) == 2


def test_weekly_audit_omits_structured_cost_without_recovery():
    rows = build_supplemental_detail_rows(
        [
            {
                "title": "Already Structured",
                "start_date": "2026-07-14",
                "cost": "$20",
                "description": "General event description without supplemental assignments.",
            }
        ],
        week_start=date(2026, 7, 13),
    )
    assert rows == []


def test_audit_render_includes_cost_schedule_and_url():
    text = render_supplemental_detail_audit(
        [
            {
                "start_date": "2026-07-14",
                "title": "Concert",
                "venue": "Park",
                "source": "AllEvents",
                "cost": "$15",
                "cost_source": "description",
                "schedule_items": [{"time": "7 PM", "label": "Headliner"}],
                "url": "https://example.com/concert",
            }
        ]
    )
    assert "Cost: $15 (description)" in text
    assert "Schedule: 7 PM — Headliner" in text
    assert "https://example.com/concert" in text
