from src.occurrence_resolution import compare_occurrences, resolve_occurrences


def event(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "title": "Jazz Jams Hosted by Japheth Solares",
        "start_date": "2026-07-15",
        "start_time": "18:00",
        "end_time": None,
        "venue": "The Emerald of Siam",
        "venue_id": "emerald-place-id",
        "city": "Richland",
        "source": "VisitTriCities",
        "url": "https://visit.example/jazz-jams",
        "description": "Weekly jazz jam.",
    }
    values.update(overrides)
    return values


def test_resolves_cross_source_title_variation_at_same_venue_and_time() -> None:
    result = resolve_occurrences(
        [
            event(),
            event(
                title="Jazz Jams Hosted by Japheth Solares at Emerald of Siam",
                source="TriCityVibe",
                url="https://vibe.example/jazz-jams",
            ),
        ]
    )

    assert len(result.events) == 1
    assert result.events[0]["source"] == "VisitTriCities"
    assert result.events[0]["duplicate_sources"] == ["VisitTriCities", "TriCityVibe"]
    assert set(result.events[0]["source_urls"]) == {
        "https://visit.example/jazz-jams",
        "https://vibe.example/jazz-jams",
    }
    assert result.groups[0]["confidence"] >= 0.90


def test_shared_url_is_conclusive_but_not_across_dates() -> None:
    same = compare_occurrences(event(), event(source="AllEvents"))
    different_date = compare_occurrences(
        event(), event(source="AllEvents", start_date="2026-07-16")
    )

    assert same.confidence == 1.0
    assert "shared_url" in same.reasons
    assert different_date.confidence == 0.0


def test_does_not_merge_legitimate_different_session_times() -> None:
    result = resolve_occurrences(
        [event(), event(source="TriCityVibe", url="https://vibe.example/later", start_time="20:00")]
    )

    assert len(result.events) == 2
    assert all(item["publication_blocker_reason"] == "conflicting_occurrence" for item in result.events)


def test_explicit_non_overlapping_age_cohorts_are_distinct_sessions() -> None:
    result = resolve_occurrences(
        [
            event(
                title="Teen Yoga Trapeze Summer Camp (Ages 11-14)",
                start_time="12:30",
            ),
            event(
                title="Teen Yoga Trapeze Summer Camp (Ages 15-18)",
                start_time="15:00",
                source="AllEvents",
                source_event_id="older-teens",
                url="https://example.com/older-teens",
            ),
        ]
    )

    assert len(result.events) == 2
    assert result.groups == []
    assert all(not item.get("publication_blocker_reason") for item in result.events)


def test_overlapping_age_cohorts_keep_conflict_protection() -> None:
    result = resolve_occurrences(
        [
            event(title="Teen Yoga Trapeze Summer Camp (Ages 11-15)", start_time="12:30"),
            event(
                title="Teen Yoga Trapeze Summer Camp (Ages 15-18)",
                start_time="15:00",
                source="AllEvents",
                url="https://example.com/older-teens",
            ),
        ]
    )

    assert len(result.events) == 2
    assert all(item["publication_blocker_reason"] == "conflicting_occurrence" for item in result.events)


def test_conflicting_occurrence_quarantines_every_member_with_complete_provenance() -> None:
    result = resolve_occurrences(
        [
            event(
                source="NotionWeekly",
                source_event_id="weekly-sports-page",
                url="https://sportspagewa.com/",
                start_time="19:00",
                end_time="21:00",
            ),
            event(
                source="AllEvents",
                source_event_id="200030515871259",
                url="https://allevents.in/kennewick/event/200030515871259",
                start_time="12:00",
                end_time="14:00",
            ),
        ]
    )

    assert len(result.events) == 2
    assert result.groups[-1]["kind"] == "conflicting_occurrence"
    details = result.events[0]["publication_blocker_details"]
    assert {item["source"] for item in details} == {"NotionWeekly", "AllEvents"}
    assert {item["source_event_id"] for item in details} == {
        "weekly-sports-page",
        "200030515871259",
    }
    assert {item["source_url"] for item in details} == {
        "https://sportspagewa.com/",
        "https://allevents.in/kennewick/event/200030515871259",
    }
    assert {item["start_time"] for item in details} == {"19:00", "12:00"}
    assert all(item["reason"] == "conflicting_occurrence" for item in details)


def test_strongly_contained_title_with_conflicting_time_is_quarantined() -> None:
    result = resolve_occurrences(
        [
            event(title="Neon Interstate", start_time="19:00"),
            event(
                title="Neon Interstate Live at Iconic Brewing",
                source="AllEvents",
                url="https://allevents.example/neon",
                start_time="12:00",
            ),
        ]
    )

    assert len(result.events) == 2
    assert all(item["publication_blocker_reason"] == "conflicting_occurrence" for item in result.events)


def test_overlapping_concert_roster_with_conflicting_time_is_quarantined() -> None:
    result = resolve_occurrences(
        [
            event(
                title=(
                    "Los Rieleros Del Norte, Voz De Mando, Banda Rancho Viejo De Julio "
                    "Aramburo La Bandononona, Banda Zeta, Banda Pequeños Musical in Pasco"
                ),
                start_time="08:00",
            ),
            event(
                title="Pequenos Musical Los Rieleros Del Norte & Voz de Mando",
                source="AllEvents",
                source_event_id="2300030372129110",
                url="https://allevents.in/pasco/event/2300030372129110",
                start_time="12:00",
            ),
        ]
    )

    assert len(result.events) == 2
    assert all(item["publication_blocker_reason"] == "conflicting_occurrence" for item in result.events)


def test_different_same_venue_events_remain_publishable_and_separate() -> None:
    result = resolve_occurrences(
        [
            event(title="Jazz Jams", start_time="18:00"),
            event(
                title="Comedy Showcase",
                source="TriCityVibe",
                url="https://vibe.example/comedy",
                start_time="20:00",
            ),
        ]
    )

    assert len(result.events) == 2
    assert all(not item.get("publication_blocker_reason") for item in result.events)


def test_does_not_merge_same_title_at_different_venues() -> None:
    result = resolve_occurrences(
        [
            event(title="Open Mic"),
            event(
                title="Open Mic",
                source="TriCityVibe",
                url="https://vibe.example/open-mic",
                venue="Longship Cellars",
                venue_id="longship-place-id",
            ),
        ]
    )

    assert len(result.events) == 2


def test_source_priority_selects_primary_and_preserves_provenance() -> None:
    result = resolve_occurrences(
        [
            event(source="AllEvents", url="https://all.example/jazz", description=""),
            event(source="VisitTriCities", url="https://visit.example/jazz"),
        ]
    )

    resolved = result.events[0]
    assert resolved["source"] == "VisitTriCities"
    assert resolved["duplicate_count"] == 2
    decision = resolved["intelligence"]["occurrence_resolution"]
    assert decision["confidence"] >= 0.90
    assert "same_venue" in decision["reason"]


def test_resolves_venue_alias_when_one_source_lacks_registry_id() -> None:
    result = resolve_occurrences(
        [
            event(title="The Generations"),
            event(
                title="The Generations at Emerald of Siam",
                source="TriCityVibe",
                url="https://vibe.example/generations",
                venue="Emerald of Siam",
                venue_id=None,
                venue_registry_name=None,
            ),
        ]
    )

    assert len(result.events) == 1
    reason = result.events[0]["intelligence"]["occurrence_resolution"]["reason"]
    assert "same_canonical_venue" in reason


def test_resolves_promotional_venue_suffix() -> None:
    result = resolve_occurrences(
        [
            event(
                title="Frazer Wambeke",
                venue="Longship Cellars",
                venue_id=None,
                url="https://visit.example/frazer",
                start_date="2026-07-16",
                start_time="16:30",
            ),
            event(
                title="Frazer Wambeke at Longship Cellars",
                venue="Longship Cellars",
                venue_id=None,
                source="TriCityVibe",
                url="https://vibe.example/frazer",
                start_date="2026-07-16",
                start_time="16:30",
            ),
        ]
    )

    assert len(result.events) == 1


def test_resolves_minor_title_typo_with_same_venue_and_time() -> None:
    result = resolve_occurrences(
        [
            event(
                title="Joshua Peace Saxxidelic",
                venue="Solar Spirits",
                venue_id=None,
                url="https://visit.example/joshua",
                start_date="2026-07-17",
                start_time="20:00",
            ),
            event(
                title="Josua Peace Saxxidelic",
                venue="Solar Spirits Distillery Tasting Room",
                venue_id=None,
                source="TriCityVibe",
                url="https://vibe.example/josua",
                start_date="2026-07-17",
                start_time="20:00",
            ),
        ]
    )

    assert len(result.events) == 1


def test_resolves_hospitality_venue_long_and_short_names() -> None:
    evidence = compare_occurrences(
        event(
            title="Angel Urrea",
            venue="Goose Ridge Winery",
            venue_id=None,
            start_date="2026-07-17",
            start_time="17:00",
        ),
        event(
            title="Angel Urrea at Goose Ridge Winery",
            venue="Goose Ridge Estate Vineyards and Winery",
            venue_id=None,
            source="TriCityVibe",
            url="https://vibe.example/angel",
            start_date="2026-07-17",
            start_time="17:00",
        ),
    )

    assert evidence.confidence >= 0.90
    assert "same_canonical_venue" in evidence.reasons


def test_missing_times_require_exceptionally_strong_title_evidence() -> None:
    different = resolve_occurrences(
        [
            event(title="Summer Market", start_time=None, venue_id=None),
            event(
                title="Summer Music",
                start_time=None,
                venue_id=None,
                source="TriCityVibe",
                url="https://vibe.example/summer-music",
            ),
        ]
    )

    assert len(different.events) == 2


def test_preserves_breakfast_workshop_and_evening_class_as_distinct():
    result = resolve_occurrences([
        event(title="Young Bakers Focaccia", start_time="11:00", description="Breakfast hands-on workshop."),
        event(title="Young Bakers Focaccia Class", start_time="18:00", description="Evening class.", source="AllEvents", url="https://example.test/evening"),
    ])
    assert len(result.events) == 2
    assert all(not item.get("publication_blocker_reason") for item in result.events)


def test_preserves_music_festival_and_drag_show_as_distinct():
    result = resolve_occurrences([
        event(title="Les-Be-Emo", start_time="10:00", description="A mini music festival with three bands."),
        event(title="Les-Be-Emo Drag Show", start_time="13:00", description="A hosted drag show with lip-sync performances.", source="AllEvents", url="https://example.test/drag"),
    ])
    assert len(result.events) == 2
    assert all(not item.get("publication_blocker_reason") for item in result.events)


def test_merges_overall_event_with_explicit_nested_band_window():
    result = resolve_occurrences([
        event(title="FORTY Celebrating 40 Years Austin Miller Full Band", start_time="17:00", description="Celebration starts at 5 PM; Austin Miller band takes the Main Lawn 6 PM - 9 PM."),
        event(title="FORTY Austin Miller Full Band", start_time="18:00", description="", source="TriCityVibe", url="https://example.test/band"),
    ])
    assert len(result.events) == 1
    assert result.events[0]["start_time"] == "17:00"
    assert "nested_performance_start_matches" in result.events[0]["intelligence"]["occurrence_resolution"]["reason"]


def test_merges_contained_anniversary_performance_window():
    result = resolve_occurrences([
        event(title="Iconic Brewing Anniversary Celebration with Stoney Lonesome", start_time="17:00", end_time="22:00"),
        event(title="Anniversary Celebration with Stoney Lonesome at Iconic Brewing", start_time="18:00", end_time="22:00", source="TriCityVibe", url="https://example.test/stoney"),
    ])
    assert len(result.events) == 1
    assert result.events[0]["start_time"] == "17:00"
