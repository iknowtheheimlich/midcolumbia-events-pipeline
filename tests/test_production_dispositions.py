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


def test_mc_2026_033_disposition_manifest_covers_all_conflict_cohorts_and_exclusions() -> None:
    dispositions = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)

    assert dispositions is not None
    assert dispositions.mission_id == "MC-2026-033"
    assert len(dispositions.resolutions) == 10
    assert len(dispositions.exclusions) == 3
    selector_ids = {
        selector.get("source_event_id")
        for cohort in (*dispositions.resolutions, *dispositions.exclusions)
        for selector in cohort["selectors"]
    }
    assert "200030535883055" in selector_ids
    assert "200030535883258" in selector_ids
    assert {cohort["reason"] for cohort in dispositions.exclusions} == {"captain_excluded_this_week"}
    excluded_cohorts = {cohort["cohort"] for cohort in dispositions.exclusions}
    assert any(cohort.startswith("HAPO Center regional concert cohort") for cohort in excluded_cohorts)
    assert any(cohort.startswith("Richland Estate Sale") for cohort in excluded_cohorts)
    assert any(cohort.startswith("Team Policy Debate Camp") for cohort in excluded_cohorts)
    # Ten corrected cohorts plus the deliberately excluded HAPO conflict account
    # for all eleven conflicting-occurrence cohorts from the Captain review.
    assert len(dispositions.resolutions) + 1 == 11


def test_sports_page_external_authority_resolves_to_one_supported_occurrence() -> None:
    dispositions = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)
    assert dispositions is not None
    sunday_disposition = ProductionDispositions(
        dispositions.mission_id,
        dispositions.week_start,
        (dispositions.resolutions[-1],),
        (),
    )
    sunday = sunday_disposition.apply([
        {**_event("AllEvents", "200030535883055", start_time="09:00", title="R0CK'N Bingo"), "start_date": "2026-08-16", "venue": "Sports Page Bar & Grill"},
        {**_event("AllEvents", "200030535883258", start_time="08:00", title="R0CK'N Bingo + Rockstar Trivia"), "start_date": "2026-08-16", "venue": "Sports Page Bar & Grill"},
    ])
    result = resolve_occurrences(sunday)

    assert len(result.events) == 1
    event = result.events[0]
    assert event["title"] == "Game Night Live R0CK'N Bingo"
    assert event["start_time"] == "16:00"
    assert event["end_time"] == "18:00"
    assert not event.get("publication_blocker_reason")
    decision = event["intelligence"]["captain_disposition"]
    assert decision["reason"] == "captain_approved_external_authority"
    assert decision["value"]["evidence_authority"] == "first_party_organizer_schedule"
    assert decision["value"]["evidence_url"] == "https://gamenightlive.com/washington-tri-cities/"


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
