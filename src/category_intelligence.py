"""Explainable semantic category enrichment for canonical events.

This layer classifies what an event is. Organizer and venue intelligence supply priors;
neither overrides stronger title or source evidence. Organizer evidence precedes venue
evidence because organizers travel while physical venues frequently host mixed programs.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from src.classification_observability import attach_classification_observability
from src.organizer_category_intelligence import organizer_category_hint
from src.publishing_contract import PublishingProfile
from src.venue_category_intelligence import venue_category_hint

_SPACE_RE = re.compile(r"\s+")
_COMMUNITY_AUTHORITY_RE = re.compile(
    r"\b(?:public library|library system|libraries|library|historical society|history museum|"
    r"museum|heritage (?:center|institution|museum|society)|city of [^|,]+|county of [^|,]+|"
    r"[^|,]+ county|parks? (?:and|&) recreation|parks? department|municipal|community center|"
    r"public center)\b",
    re.IGNORECASE,
)
_PRIVATE_OR_COMMERCIAL_AUTHORITY_RE = re.compile(
    r"\b(?:llc|inc\.?|corp(?:oration)?|company|co\.?|winery|brew(?:ery|ing)|distillery|"
    r"restaurant|bar|saloon|casino|church|ministry|studio|collective|wellness|yoga|fitness|"
    r"academy|school|university|college)\b",
    re.IGNORECASE,
)
_TRUSTED_COMMUNITY_AUTHORITY_SOURCES = {
    "richlandlibrary",
    "midcolumbialibraries",
}
_COMMUNITY_DESCRIPTION_AUTHORITY_RE = re.compile(
    r"\b(?:the\s+(?:public\s+)?library['’]s|presented\s+by\s+(?:the\s+)?[^.]{0,80}\blibrar(?:y|ies)|"
    r"hosted\s+by\s+(?:the\s+)?(?:city|county|[^.]{0,60}\bparks?\s+(?:and|&)\s+recreation|"
    r"[^.]{0,60}\bpublic\s+library|[^.]{0,60}\bhistorical\s+society|[^.]{0,60}\bmuseum)|"
    r"\bat\s+(?:the\s+)?[^.]{0,50}\blibrary\b)",
    re.IGNORECASE,
)
_INSTRUCTION_EVIDENCE_RE = re.compile(
    r"\b(?:class(?:es)?|workshop|101|clinic|lesson|guided instruction|hands-on instruction|"
    r"instruction(?:al)?|instructor|learn to|pilates|self-defense|self defense|line danc(?:e|ing)|"
    r"dance instruction|yoga instruction|yoga day camp|yoga trapeze|ceramics?|blending lab|"
    r"cooking instruction|pasta making|make (?:a|an|your)|create (?:a|an|your)|"
    r"(?:will\s+)?guide you through (?:creating|making))\b",
    re.IGNORECASE,
)
_CAMP_RE = re.compile(r"\bcamp\b", re.IGNORECASE)
_FUNDRAISING_EVIDENCE_RE = re.compile(
    r"\b(?:benefit(?:ing|ting)|(?:all\s+)?proceeds\s+(?:go to|support|benefit(?:ing|ting))|for a cause|"
    r"fundrais(?:er|ing)\s+for|(?:silent\s+auction|raffle)[^.]{0,120}\b(?:support|help)\b)\b",
    re.IGNORECASE,
)
_SOCIAL_EVENT_RE = re.compile(
    r"\b(?:family night|grand opening|back to school bash|summer bash|party|shop crawl|plant swap|"
    r"networking luncheon|get together|team bonding|join the gang|supportive (?:space|gathering))\b",
    re.IGNORECASE,
)
_PERFORMANCE_EVIDENCE_RE = re.compile(
    r"\b(?:concert|live music|live musical performance|performing live|live band|musical performance|"
    r"music series|concert series|performer series|bands?)\b",
    re.IGNORECASE,
)

_CORROBORATED_LIVE_PERFORMER_RE = re.compile(
    r"(?:\b(?:live|performing)\s+(?:in|at)\s+[^|]{2,80}\b.*\b(?:artist|singer|songwriter|hits?|show)\b|"
    r"\b(?:artist|singer|songwriter|hits?|show)\b.*\b(?:live|performing)\s+(?:in|at)\b|"
    r"\bbiggest hits?\b.*\bbrought to life\b)",
    re.IGNORECASE,
)
_STAGED_PERFORMANCE_RE = re.compile(
    r"\b(?:drag (?:pageant|show)|cabaret|burlesque show|theatrical (?:production|experience)|folk opera)\b",
    re.IGNORECASE,
)
_FAITH_PROGRAM_RE = re.compile(
    r"\b(?:worship|preaching|bible (?:trivia|knowledge(?: during)? trivia)|evangelistic|prophetic (?:ministry|intensive|prayer)|"
    r"relief society|elders quorum|ward (?:activity|program)|church community|denominational|"
    r"holy spirit conference|constituency session|yw/ym activity|faith[- ]filled|"
    r"church community|congregation (?:luau|program)|devotional)\b",
    re.IGNORECASE,
)
_FAITH_AUTHORITY_RE = re.compile(
    r"\b(?:church|ward|congregation|ministry|pastor|denomination|latter[- ]day saints?|lds|"
    r"adventist|catholic|christian|gospel|faith|temple|christ|god.s|gracepoint|npuc)\b",
    re.IGNORECASE,
)
_PUBLIC_TALK_EVIDENCE_RE = re.compile(
    r"\b(?:in this talk|explor(?:e|ing) (?:the )?(?:basic )?(?:principles|history|stories)|"
    r"learn (?:about )?(?:their|the) (?:history|stories))\b",
    re.IGNORECASE,
)
_LIBRARY_PROGRAM_EVIDENCE_RE = re.compile(
    r"\b(?:library|libraries)\b[\s\S]{0,180}\b(?:learn|learning|craft|stencil|stem|science|history|games?|gaming|stories|educational|program)\b|"
    r"\b(?:learn|learning|craft|stencil|stem|science|history|games?|gaming|stories|educational|program)\b[\s\S]{0,180}\b(?:library|libraries)\b",
    re.IGNORECASE,
)
_SURPLUS_SALE_RE = re.compile(
    r"\bsurplus sale\b(?=[\s\S]{0,220}\b(?:as[- ]is|items?|goods?|purchase|buyer|remove|removal)\b)",
    re.IGNORECASE,
)


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


_EXPLICIT_TITLE_RULES: tuple[CategoryRule, ...] = (
    _rule("Karaoke/Open Mic", 0.99, "karaoke_or_open_mic", r"\b(?:karaoke|kareoke|open[ -]?mic)\b"),
    _rule(
        "Classes/Workshops",
        0.99,
        "explicit_class_or_workshop",
        r"\b(?:class(?:es)?|workshop|101|lesson|training|guided instruction|hands-on instruction|instruction(?:al)?|instructor|learn to|build-it|build it|diy|pilates|self-defense|self defense)\b|\b(?:intro|intermediate) to\b",
    ),
    _rule(
        "Classes/Workshops",
        0.99,
        "participatory_visual_art",
        r"\b(?:painting with glass|fused glass|suncatcher|resin art|paint night|paint party|sip and paint|sip & paint|paint a ceramic|ceramic painting|pottery painting|cartoon creation|alcohol ink|watercolor|mixed media)\b",
    ),
    _rule(
        "Food & Drink",
        0.99,
        "explicit_food_or_winemaker_event",
        r"\b(?:visiting winemaker|winemaker night|winemaker takeover|farm to fork|wine en blanc|paella|pairing)\b",
    ),
    _rule(
        "Music/Comedy",
        0.99,
        "explicit_live_performance",
        r"\b(?:live\s+(?:at|@)|in concert|live music)\b|\bsaxxidelic\b",
    ),
)


_TITLE_RULES: tuple[CategoryRule, ...] = (
    _rule("Estate/Yard/Garage Sales", 0.99, "estate_or_yard_sale", r"\b(?:estate|yard|garage|rummage) sale\b"),
    _rule("Karaoke/Open Mic", 0.99, "karaoke_or_open_mic", r"\b(?:karaoke|kareoke|open[ -]?mic)\b"),
    _rule("Trivia/Game Night", 0.98, "trivia_or_game_night", r"\b(?:trivia|bingo|game night|speed puzzling)\b"),
    _rule("Markets", 0.98, "market", r"\b(?:farmers'? market|night market|community market|vendor market|market)\b"),
    _rule("Fundraisers", 0.97, "fundraiser", r"\b(?:fundrais(?:er|ing)|benefit concert|benefit(?:ing|ting)|proceeds support|proceeds benefit(?:ing|ting)|for a cause|donor party|charity)\b"),
    _rule("Tours", 0.97, "tour", r"\b(?:guided|walking|museum|b reactor) tour\b|\batomic explorations\b"),
    _rule(
        "Sports",
        0.97,
        "sports_competition",
        r"\b(?:baseball|basketball|football|soccer|volleyball|run club|5k|10k|tournament|classic|showdown|game vs\.?|dust devils|alumni game)\b",
    ),
    _rule(
        "Lectures/Talks",
        0.97,
        "lecture_or_history_talk",
        r"\b(?:lecture|author talk|book talk|history talk|historical presentation|speaker series|black paratroopers|town hall|supplier connect|museum association presents|b reactor museum association|ice age floods|go-stem|science caf[eé]|seminar|panel discussion|chronic heart failure education)\b",
    ),
    _rule("Food & Drink", 0.97, "food_or_drink_experience", r"\b(?:wine|beer|cocktail|cake|chip|cheese|food) pairings?\b|\b(?:paella|farm to fork|wine en blanc|winemaker takeover|tasting dinner|tea party)\b"),
    _rule("Art/Theater", 0.97, "film_or_theater", r"\b(?:movie|movies|film|cinema|stage play|theatrical|theatre|theater|musical|improv comedy|art show|gallery|exhibition|auditions?|newsies)\b"),
    _rule("Festivals/Fair", 0.96, "festival_or_fair", r"\b(?:festival|fest|fair|parade|celebration)\b"),
    _rule("Faith Based", 0.96, "religious_program", r"\b(?:church service|worship|bible study|ministry|prayer group|faith service|vacation bible school|vbs|ward youth activity|fhe|noche de hogar)\b"),
    _rule("School District Event", 0.96, "school_district", r"\b(?:school board|school district|pta|graduation|school open house)\b"),
    _rule(
        "Community Programs",
        0.95,
        "library_or_community_program",
        r"\b(?:story[ -]?time|lego club|pok[eé]mon club|book club|therapy dogs?|library board|advisory board|lawn games|steamkids|teen program|baby play|music together|library gaming guild|love on a leash|community program|primordial goo|magna-saurus|sound bath|breathwork|meditation|recovery dharma|cacao ceremony|new moon gathering|yoga|sensory friendly night|volunteer event)\b",
    ),
    _rule(
        "Classes/Workshops",
        0.95,
        "activity_instruction_or_craft",
        r"\b(?:cpr/aed|first aid certification|certification|paint-a-saurus|perler beads|fiber & friends|t-shirt memory quilt|felt daffodil headbands|tarot with)\b",
    ),
    _rule("Music/Comedy", 0.95, "music_or_comedy_title", r"\b(?:live music|concert|jazz|reggae|band|trio|singer|comed(?:y|ian)|music by|harpist|saxxidelic)\b"),
    _rule("Classes/Workshops", 0.94, "class_or_workshop", r"\b(?:class(?:es)?|workshop|lesson|training|build-it|build it|diy)\b|\b(?:intro|intermediate) to\b"),
    _rule("Events/Hangouts", 0.90, "community_promotion_day", r"\b(?:cow appreciation day|national hot dog day|customer appreciation|anniversary celebration)\b"),
    _rule("Events/Hangouts", 0.82, "social_event", r"\b(?:social|meet[ -]?up|hang ?out|watch party|community night|gathering|speed friending)\b"),
    _rule("Events/Hangouts", 0.91, "explicit_social_event", r"\b(?:family night|grand opening|back to school bash|summer bash|party|shop crawl|plant swap)\b"),
)


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
    "live music": "Music/Comedy",
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
    "kids and families": "Community Programs",
    "adult": "Community Programs",
}


def classify_event(event: dict[str, Any], profile: PublishingProfile | None = None) -> CategoryDecision:
    active_profile = profile or PublishingProfile.load()
    title = _text(event.get("title")) or ""
    description = _text(event.get("description")) or ""
    title_description = f"{title} | {description}"

    if _FUNDRAISING_EVIDENCE_RE.search(title_description):
        return CategoryDecision("Fundraisers", 0.97, "semantic_rule=explicit_beneficiary_or_cause")
    if _SOCIAL_EVENT_RE.search(title_description):
        return CategoryDecision("Events/Hangouts", 0.91, "semantic_rule=explicit_social_event")
    if _STAGED_PERFORMANCE_RE.search(title_description):
        return CategoryDecision("Art/Theater", 0.97, "semantic_rule=explicit_staged_performance")
    if _FAITH_PROGRAM_RE.search(title_description) and _FAITH_AUTHORITY_RE.search(
        " | ".join(str(event.get(key) or "") for key in ("title", "description", "venue", "organizer", "organization", "host", "url"))
    ):
        return CategoryDecision("Faith Based", 0.96, "semantic_rule=explicit_faith_program")
    if _SURPLUS_SALE_RE.search(title_description):
        return CategoryDecision("Estate/Yard/Garage Sales", 0.97, "semantic_rule=explicit_surplus_goods_sale")

    for rule in _EXPLICIT_TITLE_RULES:
        if rule.pattern.search(title):
            decision = CategoryDecision(rule.category, rule.confidence, f"title_rule={rule.label}")
            if _eligible_decision(event, decision):
                return decision

    if _PERFORMANCE_EVIDENCE_RE.search(title_description) or _CORROBORATED_LIVE_PERFORMER_RE.search(title_description):
        return CategoryDecision("Music/Comedy", 0.96, "semantic_rule=explicit_musical_performance")

    raw_category = _text(event.get("category"))
    existing = active_profile.normalize_category(raw_category)
    if existing:
        decision = CategoryDecision(existing, 1.0, "existing_semantic_category")
        if _eligible_decision(event, decision):
            return decision
    if raw_category:
        mapped = _SOURCE_CATEGORY_MAP.get(raw_category.casefold())
        if mapped:
            decision = CategoryDecision(mapped, 0.88, f"source_category={raw_category}")
            if _eligible_decision(event, decision):
                return decision

    source_category = _text(event.get("source_category"))
    if source_category:
        mapped = _SOURCE_CATEGORY_MAP.get(source_category.casefold())
        if mapped:
            decision = CategoryDecision(mapped, 0.88, f"source_category={source_category}")
            if _eligible_decision(event, decision):
                return decision

    for rule in _TITLE_RULES:
        if rule.pattern.search(title):
            decision = CategoryDecision(rule.category, rule.confidence, f"title_rule={rule.label}")
            if _eligible_decision(event, decision):
                return decision

    organizer_hint = organizer_category_hint(event)
    if organizer_hint is not None:
        decision = CategoryDecision(organizer_hint.category, organizer_hint.confidence, f"organizer_hint={organizer_hint.organizer_name};strength={organizer_hint.strength}")
        if _eligible_decision(event, decision):
            return decision

    venue_hint = venue_category_hint(event)
    if venue_hint is not None:
        decision = CategoryDecision(venue_hint.category, venue_hint.confidence, f"venue_hint={venue_hint.venue_name};strength={venue_hint.strength}")
        if _eligible_decision(event, decision):
            return decision

    if _INSTRUCTION_EVIDENCE_RE.search(title_description):
        return CategoryDecision("Classes/Workshops", 0.97, "semantic_rule=explicit_instruction")

    if _PUBLIC_TALK_EVIDENCE_RE.search(description) and community_programs_authority_eligible(event):
        return CategoryDecision("Lectures/Talks", 0.92, "semantic_rule=public_institution_talk")

    if _LIBRARY_PROGRAM_EVIDENCE_RE.search(title_description) and community_programs_authority_eligible(event):
        return CategoryDecision("Community Programs", 0.90, "semantic_rule=qualified_library_program")

    source = (_text(event.get("source")) or "").casefold()
    if source in _TRUSTED_COMMUNITY_AUTHORITY_SOURCES and description:
        return CategoryDecision("Community Programs", 0.88, "semantic_rule=trusted_library_program")

    venue = _text(event.get("venue")) or ""
    organization = _text(event.get("organization") or event.get("organizer") or event.get("host")) or ""
    title_venue = f"{title} | {venue} | {organization}"
    for rule in _CONTEXT_RULES:
        if rule.pattern.search(title_venue):
            if rule.label == "performer_at_hospitality_venue" and not _PERFORMANCE_EVIDENCE_RE.search(title_description):
                continue
            decision = CategoryDecision(rule.category, rule.confidence, f"context_rule={rule.label}")
            if _eligible_decision(event, decision):
                return decision

    venue_type = _text(event.get("venue_type") or event.get("registry_venue_type"))
    if venue_type and venue_type.casefold() in {"library", "community_center", "public_center", "museum", "heritage", "historical"}:
        decision = CategoryDecision("Community Programs", 0.76, f"venue_type={venue_type}")
        if _eligible_decision(event, decision):
            return decision

    description_rules = (
        _rule("Lectures/Talks", 0.86, "description_lecture", r"\b(?:lecture|presentation about|historian|history of|science presentation|educational presentation)\b"),
        _rule("Food & Drink", 0.85, "description_food_drink", r"\b(?:guided tasting|pairing flight|multi-course dinner)\b"),
        _rule("Music/Comedy", 0.84, "description_live_performance", r"\b(?:live musical performance|performing live|live band)\b"),
        _rule("Community Programs", 0.84, "description_wellness_program", r"\b(?:guided meditation|sound bath|breathwork|recovery dharma|cacao ceremony)\b"),
    )
    for rule in description_rules:
        if rule.pattern.search(description):
            decision = CategoryDecision(rule.category, rule.confidence, f"description_rule={rule.label}")
            if _eligible_decision(event, decision):
                return decision

    return CategoryDecision(None, 0.0, "no_category_rule_matched")


def enrich_event_category(event: dict[str, Any], profile: PublishingProfile | None = None) -> dict[str, Any]:
    copied = dict(event)
    decision = classify_event(copied, profile)
    if decision.category:
        copied["category"] = decision.category
    copied["category_confidence"] = decision.confidence
    copied["category_reason"] = decision.reason
    return attach_classification_observability(copied)


def enrich_event_categories(events: Iterable[dict[str, Any]], profile: PublishingProfile | None = None) -> list[dict[str, Any]]:
    active_profile = profile or PublishingProfile.load()
    return [enrich_event_category(event, active_profile) for event in events]


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = _SPACE_RE.sub(" ", str(value).strip())
    return text or None


def community_programs_authority_eligible(event: dict[str, Any]) -> bool:
    """Require a qualifying sponsoring/hosting authority for Community Programs.

    Explicit organizer/host evidence controls when present. Venue evidence is a
    fallback only when no separate organizer authority is supplied.
    """
    organizer = _text(event.get("organization") or event.get("organizer") or event.get("host"))
    if organizer:
        return bool(_COMMUNITY_AUTHORITY_RE.search(organizer)) and not bool(
            _PRIVATE_OR_COMMERCIAL_AUTHORITY_RE.search(organizer)
        )
    source = (_text(event.get("source")) or "").casefold()
    if source in _TRUSTED_COMMUNITY_AUTHORITY_SOURCES:
        return True
    description = _text(event.get("description")) or ""
    if _COMMUNITY_DESCRIPTION_AUTHORITY_RE.search(description):
        return True
    venue = _text(event.get("venue") or event.get("venue_registry_name")) or ""
    venue_type = (_text(event.get("venue_type") or event.get("registry_venue_type")) or "").casefold()
    return venue_type in {"library", "community_center", "public_center", "museum", "heritage", "historical"} or bool(
        _COMMUNITY_AUTHORITY_RE.search(venue)
    )


def _eligible_decision(event: dict[str, Any], decision: CategoryDecision) -> bool:
    return decision.category != "Community Programs" or community_programs_authority_eligible(event)
