from src.venue_intelligence_discovery import discover_venue_intelligence


def _events(venue, category_counts, *, venue_type=None):
    rows = []
    day = 1
    for category, count in category_counts.items():
        for _ in range(count):
            row = {
                "venue": venue,
                "category": category,
                "start_date": f"2026-07-{day:02d}",
            }
            if venue_type:
                row["venue_type"] = venue_type
            rows.append(row)
            day = min(day + 1, 28)
    return rows


def _candidate(events, venue):
    return next(item for item in discover_venue_intelligence(events) if item.venue_name == venue)


def test_promotes_high_purity_venue_with_sufficient_history():
    events = _events("Art YOUR Way", {"Classes/Workshops": 48, "Fundraisers": 2})
    candidate = _candidate(events, "Art YOUR Way")
    assert candidate.recommendation == "PROMOTE"
    assert candidate.dominant_category == "Classes/Workshops"
    assert candidate.dominant_percent == 0.96
    assert candidate.reason == "dominant_category_stable"


def test_small_sample_is_review_not_promotion():
    events = _events("Tiny Studio", {"Classes/Workshops": 12})
    candidate = _candidate(events, "Tiny Studio")
    assert candidate.recommendation == "REVIEW"
    assert candidate.reason == "insufficient_sample=12<25"


def test_multipurpose_venue_type_is_rejected_even_when_current_sample_is_pure():
    events = _events("Example Winery", {"Music/Comedy": 30}, venue_type="Winery")
    candidate = _candidate(events, "Example Winery")
    assert candidate.recommendation == "REJECT"
    assert candidate.reason == "excluded_venue_type=Winery"


def test_mixed_venue_is_rejected_for_low_dominance():
    events = _events("Convention Hall", {"Markets": 12, "Music/Comedy": 10, "Fundraisers": 8})
    candidate = _candidate(events, "Convention Hall")
    assert candidate.recommendation == "REJECT"
    assert candidate.reason.startswith("dominant_percent=")


def test_missing_venue_or_category_rows_are_ignored():
    events = [
        {"venue": "Art YOUR Way", "category": "Classes/Workshops"},
        {"venue": "Art YOUR Way"},
        {"category": "Classes/Workshops"},
    ]
    candidates = discover_venue_intelligence(events, minimum_events=1)
    assert len(candidates) == 1
    assert candidates[0].total_events == 1


def test_registry_name_is_preferred_for_grouping_aliases():
    events = []
    for title in ("Art YOUR Way", "Art Your Way Studio"):
        for _ in range(15):
            events.append(
                {
                    "venue": title,
                    "venue_registry_name": "Art YOUR Way",
                    "category": "Classes/Workshops",
                }
            )
    candidate = _candidate(events, "Art YOUR Way")
    assert candidate.total_events == 30
    assert candidate.recommendation == "PROMOTE"


def test_output_is_ranked_promote_review_reject():
    events = []
    events += _events("Pure Studio", {"Classes/Workshops": 30})
    events += _events("Small Studio", {"Classes/Workshops": 10})
    events += _events("Mixed Hall", {"Markets": 15, "Music/Comedy": 15})
    candidates = discover_venue_intelligence(events)
    assert [item.recommendation for item in candidates] == ["PROMOTE", "REVIEW", "REJECT"]
