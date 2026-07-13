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
