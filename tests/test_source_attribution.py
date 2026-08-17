from pathlib import Path

from adapters.registry import AdapterInfo, SOURCE_REGISTRY
from src.source_attribution import build_source_attribution, quarantine_attribution_conflicts


def _adapter(name: str, label: str | None, *, include: bool = True, priority: int = 0) -> AdapterInfo:
    return AdapterInfo(
        source_name=name, adapter_package=f"adapters.{name.casefold()}", status="active",
        fixture_path=Path(f"fixtures/{name}/events.json"), enabled=True, priority=priority,
        attribution_label=label, include_in_attribution=include,
    )


def test_single_source_attribution():
    assert build_source_attribution([_adapter("A", "Source A")]) == "This is not an all inclusive list. Events were extracted from Source A."


def test_two_source_attribution_uses_and():
    assert build_source_attribution([_adapter("A", "Source A"), _adapter("B", "Source B")]) == "This is not an all inclusive list. Events were extracted from Source A and Source B."


def test_three_source_attribution_uses_oxford_comma():
    assert build_source_attribution([_adapter("A", "Source A"), _adapter("B", "Source B"), _adapter("C", "Source C")]) == "This is not an all inclusive list. Events were extracted from Source A, Source B, and Source C."


def test_internal_source_is_excluded():
    assert build_source_attribution([_adapter("Public", "Public Source"), _adapter("Internal", None, include=False)]) == "This is not an all inclusive list. Events were extracted from Public Source."


def test_duplicate_labels_are_collapsed_without_reordering():
    assert build_source_attribution([_adapter("A", "Shared Source"), _adapter("B", "Shared Source"), _adapter("C", "Other Source")]) == "This is not an all inclusive list. Events were extracted from Shared Source and Other Source."


def test_empty_public_source_set_returns_empty_footer():
    assert build_source_attribution([_adapter("Internal", None, include=False)]) == ""


def test_enabled_registry_attribution_is_priority_ordered_and_omits_legacy_bridge():
    attribution = build_source_attribution(SOURCE_REGISTRY.enabled())
    assert attribution == (
        "This is not an all inclusive list. Events were extracted from "
        "visittri-cities.com, tricityvibe.com, Mid-Columbia Libraries, "
        "Richland Library, and allevents.in."
    )
    assert "Legacy" not in attribution


def test_unrelated_source_slug_is_quarantined():
    row = quarantine_attribution_conflicts({
        "title":"Payton Drury at Hedges Winery", "source":"TriCityVibe",
        "source_event_id":"john-boudreau-at-hedges-wines",
        "url":"https://tricityvibe.com/event/john-boudreau-at-hedges-wines/",
        "venue":"Hedges Family Estate",
    })
    assert row["publication_blocker_reason"] == "source_attribution_conflict"


def test_matching_source_slug_remains_publishable():
    row = quarantine_attribution_conflicts({
        "title":"Jamie Buckley at Last Call", "source":"TriCityVibe",
        "source_event_id":"jamie-buckley-at-last-call",
        "url":"https://tricityvibe.com/event/jamie-buckley-at-last-call/",
        "venue":"Last Call",
    })
    assert "publication_blocker_reason" not in row
