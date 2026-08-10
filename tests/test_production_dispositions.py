from src.occurrence_resolution import resolve_occurrences
from src.production_dispositions import DEFAULT_PRODUCTION_DISPOSITIONS_PATH, ProductionDispositions
from src.publisher_editorial import apply_editorial_rules, community_events, main_events
from src.publisher_projection import project_event


def _event(source: str, source_event_id: str, *, start_time: str, title: str = "Shared Event") -> dict:
    return {
        "title": title,
        "source": source,
        "source_event_id": source_event_id,
        "url": f"https://example.com/{source_event_id}",
        "start_date": "2026-08-13",
        "start_time": start_time,
        "end_time": None,
        "venue": "Test Venue",
        "city": "Richland",
        "state": "WA",
        "geo_scope": "LOCAL",
        "category": "Events/Hangouts",
    }


def test_mc_2026_033_disposition_manifest_is_exact_and_leaves_sunday_unresolved() -> None:
    dispositions = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)

    assert dispositions is not None
    assert dispositions.mission_id == "MC-2026-033"
    assert len(dispositions.resolutions) == 9
    assert len(dispositions.exclusions) == 3
    selector_ids = {
        selector.get("source_event_id")
        for cohort in (*dispositions.resolutions, *dispositions.exclusions)
        for selector in cohort["selectors"]
    }
    assert "200030535883055" not in selector_ids
    assert "200030535883258" not in selector_ids


def test_evidence_resolution_corrects_exact_records_before_occurrence_resolution() -> None:
    dispositions = ProductionDispositions(
        "MC-2026-033",
        "2026-08-10",
        ({
            "cohort": "supported cohort",
            "start_time": "19:00",
            "end_time": "21:00",
            "evidence": "explicit preserved schedule",
            "selectors": [
                {"source": "A", "source_event_id": "one"},
                {"source": "B", "source_event_id": "two"},
            ],
        },),
        (),
    )

    corrected = dispositions.apply([
        _event("A", "one", start_time="12:00"),
        _event("B", "two", start_time="19:00"),
    ])
    result = resolve_occurrences(corrected)

    assert len(result.events) == 1
    assert result.events[0]["start_time"] == "19:00"
    assert result.events[0]["end_time"] == "21:00"
    assert result.events[0]["intelligence"]["captain_disposition"]["reason"] == "captain_approved_preserved_evidence"
    assert not result.events[0].get("publication_blocker_reason")


def test_undisposed_conflicting_occurrence_remains_quarantined() -> None:
    result = resolve_occurrences([
        _event("A", "one", start_time="08:00", title="R0CK'N Bingo"),
        _event("B", "two", start_time="09:00", title="R0CK'N Bingo plus Rockstar Trivia"),
    ])

    assert len(result.events) == 2
    assert all(event["publication_blocker_reason"] == "conflicting_occurrence" for event in result.events)


def test_captain_exclusion_is_completed_rejection_and_never_renders() -> None:
    dispositions = ProductionDispositions(
        "MC-2026-033",
        "2026-08-10",
        (),
        ({
            "cohort": "excluded cohort",
            "reason": "captain_excluded_this_week",
            "evidence": "authority insufficient",
            "selectors": [{"source": "A", "source_event_id": "one"}],
        },),
    )
    excluded = dispositions.apply([_event("A", "one", start_time="12:00")])[0]
    editorial = apply_editorial_rules(project_event(excluded))

    assert editorial.publication_disposition == "REJECT"
    assert editorial.editorial_reason == "captain_excluded_this_week"
    assert main_events([editorial]) == []
    assert community_events([editorial]) == []
