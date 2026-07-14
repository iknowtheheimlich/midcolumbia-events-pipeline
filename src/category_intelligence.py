"""Explainable semantic category enrichment for canonical events.

Attempt_38_CategoryIntelligence
Attempt_48_CategoryRuleHardening
Attempt_62_CategoryCorrectionWithinTaxonomy

This layer classifies what an event is. It does not decide how Reddit renders it.
Narrow, deterministic title signals run before source categories and venue context so
participatory activities and explicit food events are not misclassified by their venue.
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


@dataclass(frozen=True)
class CategoryRule:
    category: str
    confidence: float
    label: str
    pattern: re.Pattern[str]


def _rule(category: str, confidence: float, label: str, pattern: str) -> CategoryRule:
    return CategoryRule(category, confidence, label, re.compile(pattern, re.IGNORECASE))


# These rules are deliberately narrow and run first. They represent explicit event-type
# evidence that should outrank a conflicting source category or hospitality venue context.
_EXPLICIT_TITLE_RULES: tuple[CategoryRule, ...] = (
    _rule(
        "Classes/Workshops",
        0.99,
        "explicit_class_or_workshop",
        r"\b(?:class(?:es)?|workshop|lesson|training|build-it|build it|diy)\b|\b(?:intro|intermediate) to\b",
    ),
    _rule(
        "Classes/Workshops",
        0.99,
        "participatory_visual_art",
        r"\b(?:painting with glass|fused glass|suncatcher|resin art|paint night)\b",
    ),
    _rule(
        "Food & Drink",
        0.99,
        "explicit_food_or_winemaker_event",
        r"\b(?:visiting winemaker|winemaker night|winemaker takeover|farm to fork|wine en blanc|paella|pairing)\b",
    ),
)


# Title rules are intentionally ordered from most specific to broadest. Title evidence
# outranks descriptions because source prose routinely mentions unrelated classes,
# performances, food, and venues.
_TITLE_RULES: tuple[CategoryRule, ...] = (
    _rule("Estate/Yard/Garage Sales", 0.99, "estate_or_yard_sale", r"\b(?:estate|yard|garage|rummage) sale\b"),
    _rule("Karaoke/Open Mic", 0.99, "karaoke_or_open_mic", r"\b(?:karaoke|open[ -]?mic)\b"),
    _rule("Trivia/Game Night", 0.98, "trivia_or_game_night", r"\b(?:trivia|music bingo|bingo night|game night|speed puzzling)\b"),
    _rule("Markets", 0.98, "market", r"\b(?:farmers'? market|night market|community market|vendor market|market)\b"),
    _rule("Fundraisers", 0.97, "fundraiser", r"\b(?:fundrais(?:er|ing)|benefit concert|donor party|charity)\b"),
    _rule("Tours", 0.97, "tour", r"\b(?:guided|walking|museum|b reactor) tour\b|\batomic explorations\b"),
    _rule("Sports", 0.97, "sports_competition", r"\b(?:baseball|basketball|football|soccer|volleyball|run club|5k|10k|tournament|classic|showdown|game vs\.?|dust devils)\b"),
    _rule("Lectures/Talks", 0.97, "lecture_or_history_talk", r"\b(?:lecture|author talk|history talk|historical presentation|speaker series|black paratroopers)\b"),
    _rule("Food & Drink", 0.97, "food_or_drink_experience", r"\b(?:wine|beer|cocktail|cake|chip|cheese|food) pairings?\b|\b(?:paella|farm to fork|wine en blanc|winemaker takeover|tasting dinner|tea party)\b"),
    _rule("Art/Theater", 0.97, "film_or_theater", r"\b(?:movie|movies|film|cinema|stage play|theatrical|theatre|theater|musical|improv comedy|art show|gallery|exhibition)\b"),
    _rule("Festivals/Fair", 0.96, "festival_or_fair", r"\b(?:festival|fest|fair|parade|celebration)\b"),
    _rule("Faith Based", 0.96, "religious_program", r"\b(?:church service|worship|bible study|ministry|prayer group|faith service)\b"),
    _rule("School District Event", 0.96, "school_district", r"\b(?:school board|school district|pta|graduation|school open house)\b"),
    _rule("Community Programs", 0.95, "library_or_community_program", r"\b(?:story ?time|lego club|pok[eé]mon club|book club|therapy dog|library board|advisory board|lawn games|steamkids|teen program|baby play)\b"),
    _rule("Music/Comedy", 0.95, "music_or_comedy_title", r"\b(?:live music|concert|jazz|reggae|band|trio|singer|comed(?:y|ian)|music by|harpist|saxxidelic)\b"),
    _rule("Classes/Workshops", 0.94, "class_or_workshop", r"\b(?:class(?:es)?|workshop|lesson|training|build-it|build it|diy)\b|\b(?:intro|intermediate) to\b"),
    _rule("Events/Hangouts", 0.82, "social_event", r"\b(?:social|meet[ -]?up|hang ?out|watch party|community night)\b"),
)

# Context rules require multiple signals and are evaluated only after the title rules.
_CONTEXT_RULES: tuple[CategoryRule, ...] = (
    _rule(
        "Music/Comedy",
        0.93,
        "performer_at_hospitality_venue",
        r"\b(?:winery|cellars?|distillery|spirits|saloon|bar|pub|brew(?:ery|ing)|emerald of siam|at michele.?s|goose ridge|clover island)\b",
    ),
    _rule("Food & Drink", 0.92, "hospitality_experience", r"\b(?:pairing|tasting|dinner|brunch|paella|food truck|picnic)\b"),
    _rule("Art/Theater", 0.91, "arts_context", r"\b(?:visual art|performance art|gallery|exhibition)\b"),
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
    "food-drinks": "Food & Drink",
    "food & drink": "Food & Drink",
    "festivals": "Festivals/Fair",
}


def classify_event(event: dict[str, Any], profile: PublishingProfile | None = None) -> CategoryDecision:
    active_profile = profile or PublishingProfile.load()
    title = _text(event.get("title")) or ""

    for rule in _EXPLICIT_TITLE_RULES:
        if rule.pattern.search(title):
            return CategoryDecision(rule.category, rule.confidence, f"title_rule={rule.label}")

    existing = active_profile.normalize_category(_text(event.get("category")))
    if existing:
        return CategoryDecision(existing, 1.0, "existing_semantic_category")

    source_category = _text(event.get("source_category"))
    if source_category:
        mapped = _SOURCE_CATEGORY_MAP.get(source_category.casefold())
        if mapped:
            return CategoryDecision(mapped, 0.88, f"source_category={source_category}")

    for rule in _TITLE_RULES:
        if rule.pattern.search(title):
            return CategoryDecision(rule.category, rule.confidence, f"title_rule={rule.label}")

    venue = _text(event.get("venue")) or ""
    organization = _text(event.get("organization") or event.get("organizer") or event.get("host")) or ""
    title_venue = f"{title} | {venue} | {organization}"
    for rule in _CONTEXT_RULES:
        if rule.pattern.search(title_venue):
            return CategoryDecision(rule.category, rule.confidence, f"context_rule={rule.label}")

    description = _text(event.get("description")) or ""
    description_rules = (
        _rule("Lectures/Talks", 0.86, "description_lecture", r"\b(?:lecture|presentation about|historian|history of)\b"),
        _rule("Food & Drink", 0.85, "description_food_drink", r"\b(?:guided tasting|pairing flight|multi-course dinner)\b"),
        _rule("Music/Comedy", 0.84, "description_live_performance", r"\b(?:live musical performance|performing live|live band)\b"),
    )
    for rule in description_rules:
        if rule.pattern.search(description):
            return CategoryDecision(rule.category, rule.confidence, f"description_rule={rule.label}")

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
