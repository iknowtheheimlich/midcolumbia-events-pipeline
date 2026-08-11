import pytest

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
    assert len(dispositions.resolutions) == 15
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
    captain_conflicts = dispositions.resolutions[:10]
    # Ten corrected cohorts plus the deliberately excluded HAPO conflict account
    # for all eleven conflicting-occurrence cohorts from the Captain review.
    assert len(captain_conflicts) + 1 == 11
    assert {cohort["cohort"] for cohort in dispositions.resolutions[10:14]} == {
        "Sip & Sing — Columbia Gardens — 2026-08-15",
        "Summer Market at Layered — 2026-08-15",
        "Groove Principal — Clover Island Concert Series — 2026-08-12",
        "Faith Martin and Casa Rosita Pop-Up — Hedges Family Estate — 2026-08-15",
    }
    artlab = dispositions.resolutions[14]
    assert artlab["cohort"] == "ArtLab for Kids — Richland Public Library — 2026-08-13"
    assert (artlab["start_time"], artlab["end_time"]) == ("13:00", "15:00")
    night_hawks = next(cohort for cohort in dispositions.resolutions if cohort["cohort"].startswith("The Night Hawks"))
    assert night_hawks["title"] == "The Night Hawks"


def test_sports_page_external_authority_resolves_to_one_supported_occurrence() -> None:
    dispositions = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)
    assert dispositions is not None
    sunday_disposition = ProductionDispositions(
        dispositions.mission_id,
        dispositions.week_start,
        (next(cohort for cohort in dispositions.resolutions if cohort["cohort"].startswith("Game Night Live R0CK'N Bingo")),),
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
    selector_audit = event["intelligence"]["captain_disposition_selector_audit"]
    assert selector_audit["reason"] == "captain_selector_status_recorded"
    assert selector_audit["value"]["mission_id"] == "MC-2026-033"
    assert [item["status"] for item in selector_audit["value"]["selectors"]] == [
        "matched",
        "matched_and_suppressed",
    ]


def test_sports_page_suppressed_selector_may_be_absent() -> None:
    configured = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)
    assert configured is not None
    dispositions = ProductionDispositions(
        configured.mission_id,
        configured.week_start,
        (next(cohort for cohort in configured.resolutions if cohort["cohort"].startswith("Game Night Live R0CK'N Bingo")),),
        (),
    )

    corrected = dispositions.apply([
        {
            **_event("AllEvents", "200030535883055", start_time="09:00", title="R0CK'N Bingo"),
            "start_date": "2026-08-16",
            "venue": "Sports Page Bar & Grill",
        }
    ])

    assert len(corrected) == 1
    assert corrected[0]["title"] == "Game Night Live R0CK'N Bingo"
    assert corrected[0]["start_time"] == "16:00"
    assert corrected[0]["end_time"] == "18:00"
    audit = corrected[0]["intelligence"]["captain_disposition_selector_audit"]
    assert [item["status"] for item in audit["value"]["selectors"]] == ["matched", "absent"]
    assert audit["value"]["selectors"][1]["source_event_id"] == "200030535883258"
    assert audit["value"]["selectors"][1]["role"] == "suppressed"


def test_sports_page_required_surviving_selector_must_be_present() -> None:
    configured = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)
    assert configured is not None
    dispositions = ProductionDispositions(
        configured.mission_id,
        configured.week_start,
        (next(cohort for cohort in configured.resolutions if cohort["cohort"].startswith("Game Night Live R0CK'N Bingo")),),
        (),
    )

    with pytest.raises(ValueError, match=r"\('RESOLVE', 0, 0\)"):
        dispositions.apply([
            {
                **_event("AllEvents", "200030535883258", start_time="08:00", title="R0CK'N Bingo + Rockstar Trivia"),
                "start_date": "2026-08-16",
                "venue": "Sports Page Bar & Grill",
            }
        ])


def test_unmarked_missing_resolution_selector_remains_a_hard_failure() -> None:
    dispositions = ProductionDispositions(
        "MC-2026-033",
        "2026-08-10",
        ({
            "cohort": "ordinary exact correction",
            "start_time": "19:00",
            "evidence": "both records are required",
            "selectors": [
                {"source": "A", "source_event_id": "one"},
                {"source": "B", "source_event_id": "two"},
            ],
        },),
        (),
    )

    with pytest.raises(ValueError, match=r"\('RESOLVE', 0, 1\)"):
        dispositions.apply([_event("A", "one", start_time="12:00")])


def test_exclusion_selector_cannot_be_marked_suppressed() -> None:
    dispositions = ProductionDispositions(
        "MC-2026-033",
        "2026-08-10",
        (),
        ({
            "cohort": "excluded cohort",
            "reason": "captain_excluded_this_week",
            "evidence": "must identify the excluded record",
            "selectors": [
                {"source": "A", "source_event_id": "one", "role": "suppressed"}
            ],
        },),
    )

    with pytest.raises(ValueError, match="EXCLUDE Captain disposition selectors must be required"):
        dispositions.apply([])


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


def test_artlab_preserved_evidence_resolves_exact_records_to_library_time() -> None:
    configured = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)
    assert configured is not None
    artlab = next(
        cohort for cohort in configured.resolutions if cohort["cohort"].startswith("ArtLab for Kids")
    )
    dispositions = ProductionDispositions(
        configured.mission_id, configured.week_start, (artlab,), ()
    )

    corrected = dispositions.apply([
        _event("AllEvents", "200030538706203", start_time="06:00", title="ArtLab for Kids"),
        _event("RichlandLibrary", "16753117", start_time="13:00", title="ArtLab for Kids"),
    ])
    result = resolve_occurrences(corrected)

    assert len(result.events) == 1
    assert result.events[0]["title"] == "ArtLab for Kids"
    assert result.events[0]["start_time"] == "13:00"
    assert result.events[0]["end_time"] == "15:00"
    assert not result.events[0].get("publication_blocker_reason")
    decision = result.events[0]["intelligence"]["captain_disposition"]
    assert decision["reason"] == "launch_gate_resolved_preserved_first_party_evidence"


def test_exact_disposition_cohort_consolidates_different_source_venue_presentations() -> None:
    dispositions = ProductionDispositions(
        "MC-2026-033",
        "2026-08-10",
        ({
            "cohort": "Sip & Sing — exact acceptance cohort",
            "title": "Sip & Sing",
            "start_time": "16:00",
            "end_time": "18:00",
            "evidence": "same description and address",
            "decision_reason": "acceptance_approved_preserved_evidence",
            "selectors": [
                {"source": "VisitTriCities", "source_event_id": "one"},
                {"source": "TriCityVibe", "source_event_id": "two"},
            ],
        },),
        (),
    )
    left = _event("VisitTriCities", "one", start_time="16:00", title="Sip & Sing")
    left["venue"] = "421 E Columbia Dr"
    right = _event("TriCityVibe", "two", start_time="16:00", title="Sip & Sing with Opera")
    right["venue"] = "Columbia Gardens Wine and Artisan Village"

    result = resolve_occurrences(dispositions.apply([left, right]))

    assert len(result.events) == 1
    assert result.events[0]["title"] == "Sip & Sing"
    assert result.events[0]["start_time"] == "16:00"
    assert result.events[0]["end_time"] == "18:00"
    assert "same_production_disposition_cohort" in result.groups[0]["reason"]


def test_mc_2026_033_acceptance_duplicate_cohorts_each_resolve_once() -> None:
    configured = ProductionDispositions.load("2026-08-10", DEFAULT_PRODUCTION_DISPOSITIONS_PATH)
    assert configured is not None
    dispositions = ProductionDispositions(
        configured.mission_id,
        configured.week_start,
        configured.resolutions[10:14],
        (),
    )
    records = [
        {**_event("VisitTriCities", "1296002", start_time="16:00", title="Sip & Sing"), "start_date": "2026-08-15", "venue": "421 E Columbia Dr"},
        {**_event("TriCityVibe", "ben-naught", start_time="16:00", title="Sip & Sing with Mid-Columbia Opera"), "start_date": "2026-08-15", "venue": "Columbia Gardens"},
        {**_event("VisitTriCities", "1298972", start_time="10:00", title="Summer Market at Layered"), "start_date": "2026-08-15", "venue": "Layered Cake Artistry"},
        {**_event("AllEvents", "200030413213756", start_time="10:00", title="Summer Market at Layered Cake Artistry"), "start_date": "2026-08-15", "venue": "117 W Kennewick Avenue"},
        {**_event("TriCityVibe", "groove-principal-clover-island-concert-series", start_time="18:00", title="Groove Principal at the Clover Island Concert Series"), "start_date": "2026-08-12", "venue": "Clover Island Stage"},
        {**_event("AllEvents", "100001984681812728", start_time="11:00", title="Clover Island Concert Series - Groove Principal"), "start_date": "2026-08-12", "venue": "Clover Island Inn"},
        {**_event("VisitTriCities", "1300892", start_time="12:00", title="Live Music with Faith Martin and Casa Rosita Pop-Up"), "start_date": "2026-08-15", "venue": "53511 N Sunset Rd"},
        {**_event("TriCityVibe", "faith-martin-at-hedges-wines", start_time="13:00", title="Faith Martin at Hedges Family Estate Wine"), "start_date": "2026-08-15", "venue": "Hedges Family Estate Wine"},
    ]

    result = resolve_occurrences(dispositions.apply(records))

    assert len(result.events) == 4
    resolved = {event["title"]: (event["start_time"], event["end_time"]) for event in result.events}
    assert resolved == {
        "Sip & Sing": ("16:00", "18:00"),
        "Summer Market at Layered Cake Artistry": ("10:00", "16:00"),
        "Groove Principal": ("18:00", None),
        "Faith Martin and Casa Rosita Pop-Up": ("12:00", "16:00"),
    }
    assert all(not event.get("publication_blocker_reason") for event in result.events)


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
