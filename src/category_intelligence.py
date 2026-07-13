"""Explainable semantic category enrichment for canonical events.

Attempt_38_CategoryIntelligence

This layer classifies what an event is. It does not decide how Reddit renders it.
Existing valid semantic categories are preserved; deterministic rules enrich only
missing categories and always emit confidence plus an explanation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from src.publishing_contract import PublishingProfile

_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class CategoryDecision:
    category: str | None
    confidence: float
    reason: str


# Ordered from most specific to broadest. First match wins.
_RULES: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("Estate/Yard/Garage Sales", 0.99, ("estate sale", "yard sale", "garage sale", "rummage sale")),
    ("Karaoke/Open Mic", 0.99, ("karaoke", "open mic", "open-mic")),
    ("Trivia/Game Night", 0.98, ("trivia", "music bingo", "bingo night", "game night", "speed puzzling")),
    ("Markets", 0.98, ("market", "farmers market", "night market", "vendor fair", "craft fair")),
    ("Festivals/Fair", 0.97, ("festival", "fest ", " fair", "fair ", "parade", "celebration")),
    ("Fundraisers", 0.97, ("fundraiser", "fundraising", "benefit concert", "donor party", "charity")),
    ("Tours", 0.97, ("guided tour", "walking tour", "museum tour", "b reactor tour", "atomic explorations")),
    ("Sports", 0.96, ("baseball", "basketball", "football", "soccer", "volleyball", "run club", "5k", "10k", "tournament", "game vs", "dust devils")),
    ("Faith Based", 0.96, ("church", "worship", "bible study", "faith", "ministry", "prayer")),
    ("School District Event", 0.96, ("school board", "school district", "pta", "graduation", "open house")),
    ("Classes/Workshops", 0.94, ("class", "workshop", "lesson", "learn & play", "learn and play", "training", "build-it", "build it", "diy:", "intro to ", "intermediate ")),
    ("Community Programs", 0.94, ("storytime", "story time", "lego club", "pokemon club", "pokémon club", "book club", "therapy dog", "library board", "advisory board", "lawn games", "steamkids", "teen program", "baby play")),
    ("Art/Theater", 0.93, ("theater", "theatre", "play", "musical", "gallery", "painting", "fused glass", "art show", "movie", "film", "cinema", "improv")),
    ("Music/Comedy", 0.92, ("live music", "concert", "jazz", "band", "trio", "singer", "comedy", "music by", " at emerald", " at longship", " at solar spirits", " at goose ridge")),
    ("Restaurants/Bars/Wineries", 0.90, ("wine pairing", "winemaker", "winery", "cocktail", "paella", "farm to fork", "food truck", "picnic", "tea party", "dinner")),
    ("Events/Hangouts", 0.80, ("social", "meetup", "meet-up", "hangout", "hang out", "party", "community night")),
)

_SOURCE_CATEGORY_MAP = {
    "music": "Music/Comedy",
    "concerts": "Music/Comedy",
    "sports": "Sports",
    "art": "Art/Theater",
    "theatre": "Art/Theater",
    "theater": "Art/Theater",
    "workshops": "Classes/Workshops",
    "classes": "Classes/Workshops",
    "business": "Events/Hangouts",
    "food-drinks": "Restaurants/Bars/Wineries",
    "food & drink": "Restaurants/Bars/Wineries",
    "festivals": "Festivals/Fair",
}


def classify_event(event: dict[str, Any], profile: PublishingProfile | None = None) -> CategoryDecision:
    active_profile = profile or PublishingProfile.load()
    existing = active_profile.normalize_category(_text(event.get("category")))
    if existing:
        return CategoryDecision(existing, 1.0, "existing_semantic_category")

    source_category = _text(event.get("source_category"))
    if source_category:
        mapped = _SOURCE_CATEGORY_MAP.get(source_category.casefold())
        if mapped:
            return CategoryDecision(mapped, 0.88, f"source_category={source_category}")

    haystack = " | ".join(
        value
        for value in (
            _text(event.get("title")),
            _text(event.get("description")),
            _text(event.get("venue")),
            _text(event.get("organization") or event.get("organizer") or event.get("host")),
        )
        if value
    ).casefold()

    for category, confidence, needles in _RULES:
        for needle in needles:
            if needle in haystack:
                return CategoryDecision(category, confidence, f"keyword={needle.strip()}")

    venue_type = _text(event.get("venue_type") or event.get("registry_venue_type"))
    if venue_type and venue_type.casefold() in {"library", "school"}:
        return CategoryDecision("Community Programs", 0.76, f"venue_type={venue_type}")

    return CategoryDecision(None, 0.0, "no_category_rule_matched")


def enrich_event_category(event: dict[str, Any], profile: PublishingProfile | None = None) -> dict[str, Any]:
    copied = dict(event)
    decision = classify_event(copied, profile)
    if decision.category:
        copied["category"] = decision.category
    copied["category_confidence"] = decision.confidence
    copied["category_reason"] = decision.reason
    return copied


def enrich_event_categories(events: Iterable[dict[str, Any]], profile: PublishingProfile | None = None) -> list[dict[str, Any]]:
    active_profile = profile or PublishingProfile.load()
    return [enrich_event_category(event, active_profile) for event in events]


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = _SPACE_RE.sub(" ", str(value).strip())
    return text or None
