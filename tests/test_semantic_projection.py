from src.production_dispositions import ProductionDispositions
from src.semantic_projection import transform_semantic_occurrences


def event(**changes):
    row={"title":"Craft Collective: Stenciled Book Edges","start_date":"2026-08-18","occurrence_date":"2026-08-18","source_start_date":"2026-08-18","source_end_date":"2026-08-18","start_time":"18:00","end_time":"19:30","source_time_evidence":{"start_time":"18:00","end_time":"19:30"},"venue":"Kennewick Branch - Mid-Columbia Libraries","city":"Kennewick","source":"AllEvents","source_event_id":"one","url":"https://example.test/one","description":"Stencil book edges at the Kennewick library","event_kind":"single","captain_state":{}}
    row.update(changes); return row


def test_live_and_frozen_paths_share_semantic_consolidation():
    rows=[event(),event(title="The Craft Collective: Stenciled Book Edges",venue="Kennewick Mid-Columbia Library",source="MidColumbiaLibraries",source_event_id="two")]
    live=transform_semantic_occurrences(rows,deduplicate=True)
    frozen=transform_semantic_occurrences(rows,deduplicate=True,apply_time_semantics=True)
    assert len(live.events)==len(frozen.events)==1
    assert live.duplicate_groups[0]["reason"]==frozen.duplicate_groups[0]["reason"]


def test_exclusive_midnight_final_occurrence_is_removed():
    result=transform_semantic_occurrences([event(start_date="2026-08-23",occurrence_date="2026-08-23",source_start_date="2026-08-22",source_end_date="2026-08-23",start_time="20:00",end_time="00:00",source_time_evidence={"start_time":"20:00","end_time":"00:00"})])
    assert result.events==[]
    assert len(result.phantom_occurrences)==1


def test_similar_but_distinct_programs_remain_separate():
    pairs=[
        (event(title="Les-Be-Emo",start_time="17:00",venue="Azucar",source_event_id="one"),event(title="Les-Be-Emo Drag Show",start_time="20:00",venue="Azucar",source_event_id="two")),
        (event(title="Live Music with Common Thread Duo at The Peacock",venue="The Peacock",source_event_id="three"),event(title="Live Music with Dane Pollard at The Peacock",venue="The Peacock",source="VisitTriCities",source_event_id="four")),
        (event(title="Monday Night Poker",venue="Tin Hat Tavern",city="Kennewick",source_event_id="five"),event(title="Monday Night Poker Game",venue="American Legion",city="Pasco",source="NotionWeekly",source_event_id="six")),
        (event(title="Game Night Live Trivia",start_time="18:00",venue="Iconic Brewing",source_event_id="seven"),event(title="Game Night Live",start_time="19:00",venue="Rattlesnake Mountain Brewing",source="NotionWeekly",source_event_id="eight")),
    ]
    for left,right in pairs:
        assert len(transform_semantic_occurrences([left,right]).events)==2


def test_contradictory_captain_decisions_fail_closed():
    rows=[event(captain_state={"Captain Include":"INCLUDE"}),event(title="The Craft Collective: Stenciled Book Edges",source="MidColumbiaLibraries",source_event_id="two",captain_state={"Captain Include":"EXCLUDE"})]
    try: transform_semantic_occurrences(rows)
    except ValueError as exc: assert "contradictory Captain decisions" in str(exc)
    else: raise AssertionError("contradictory Captain state did not fail closed")


def test_compatible_captain_decisions_consolidate():
    state={"Captain Include":"INCLUDE","Captain Category":"Classes/Workshops"}
    rows=[event(captain_state=state),event(title="The Craft Collective: Stenciled Book Edges",source="MidColumbiaLibraries",source_event_id="two",captain_state=state)]
    assert len(transform_semantic_occurrences(rows).events)==1


def test_quarantined_source_is_provenance_not_visible_authority():
    valid=event(title="After Hours at Hedges: Payton Layne Drury",venue="Hedges Family Estate",source="VisitTriCities",source_event_id="1300893",url="https://valid.example/",captain_state={"Captain Title Override":"Payton Layne Drury"})
    stale=event(title="Payton Drury at Hedges Winery",venue="Hedges Family Estate Wine",source="TriCityVibe",source_event_id="john-boudreau-at-hedges-wines",url="https://tricityvibe.com/event/john-boudreau-at-hedges-wines/",captain_state={"Captain Title Override":"Payton Drury"})
    result=transform_semantic_occurrences([valid,stale])
    assert len(result.events)==1
    assert result.events[0]["source"]=="VisitTriCities"
    assert {item["source"] for item in result.events[0]["dedupe_provenance"]}=={"VisitTriCities","TriCityVibe"}


def test_replay_safe_unknown_time_disposition_uses_shared_policy():
    policy=ProductionDispositions("mission","2026-08-17",({"cohort":"AquaSox","time_unknown":True,"evidence":"Captain decision","selectors":[{"source":"AllEvents","source_event_id":"aqua"}]},),())
    result=transform_semantic_occurrences([event(source_event_id="aqua",start_time="07:00",end_time="07:59")],production_dispositions=policy)
    assert result.events[0]["start_time"] is None
    assert result.events[0]["end_time"] is None
