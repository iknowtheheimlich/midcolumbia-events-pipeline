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
