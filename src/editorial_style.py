"""Configurable presentation cleanup for publisher-facing events.

Attempt_40_EditorialStyleIntelligence
Attempt_50_VenuePresentationProfile
Attempt_60_TitleCanonicalization

Canonical source fields remain unchanged. Title cleanup remains editorial policy; venue
cleanup is a compatibility path used only when no authoritative venue presentation exists.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


DEFAULT_STYLE_PATH = Path("config/editorial_style.json")
_SPACE_RE = re.compile(r"\s+")
_ADDRESS_RE = re.compile(
    r"^\d{1,6}\s+.+?(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|place|pl|way|boulevard|blvd|court|ct)\b",
    re.IGNORECASE,
)
_TERMINAL_DATE_RE = re.compile(
    r"(?:\s*(?:::|[-–—])?\s*)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\s*$",
    re.IGNORECASE,
)
_MUSIC_CATEGORY = "music/comedy"
_MUSIC_LEADING_PROMO_RE = re.compile(
    r"^(?:(?:free\s+)?live(?:\s+music)?[!,:\s-]*(?:with|w/)?\s+)",
    re.IGNORECASE,
)
_MUSIC_ACTION_SUFFIX_RE = re.compile(
    r"^(.+?)\s+(?:rocks?|rocking|performs?|performing|plays?|playing)\b.*$",
    re.IGNORECASE,
)
_MUSIC_LIVE_VENUE_SUFFIX_RE = re.compile(
    r"\s*[,|:-]?\s*live\s+(?:at|@)\s+.+?[!.,]*$",
    re.IGNORECASE,
)
_MUSIC_PROMO_SENTENCE_RE = re.compile(
    r"\s*!\s*(?:thirsty\s+thursday|friday\s+night|saturday\s+night|sunday\s+funday).*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EditorialStyleProfile:
    strip_prefixes: tuple[str, ...]
    venue_aliases: dict[str, str]
    strip_terminal_date: bool = True
    deconflict_title_venue: bool = True
    profile_version: int = 1

    @classmethod
    def load(cls, path: Path = DEFAULT_STYLE_PATH) -> "EditorialStyleProfile":
        payload = json.loads(path.read_text(encoding="utf-8"))
        aliases = {
            _key(key): _clean(value)
            for key, value in (payload.get("venue_aliases") or {}).items()
            if _clean(key) and _clean(value)
        }
        return cls(
            strip_prefixes=tuple(
                _clean(value)
                for value in payload.get("strip_prefixes", [])
                if _clean(value)
            ),
            venue_aliases=aliases,
            strip_terminal_date=bool(payload.get("strip_terminal_date", True)),
            deconflict_title_venue=bool(payload.get("deconflict_title_venue", True)),
            profile_version=int(payload.get("profile_version", 1)),
        )


def derive_display_fields(
    title: str,
    venue: str,
    city: str | None,
    *,
    category: str | None = None,
    profile: EditorialStyleProfile | None = None,
    preserve_venue: bool = False,
) -> tuple[str, str, str]:
    """Return display title, display venue, and an explainable style reason."""
    active = profile or EditorialStyleProfile.load()
    original_title = _clean(title)
    original_venue = _clean(venue)
    display_venue = original_venue if preserve_venue else _display_venue(original_venue, city, active)
    display_title = _display_title(original_title, display_venue, category, active)

    reasons: list[str] = []
    if display_venue != original_venue:
        reasons.append("venue_presentation")
    if display_title != original_title:
        reasons.append("title_cleanup")
    return display_title, display_venue, "+".join(reasons) or "unchanged"


def _display_venue(venue: str, city: str | None, profile: EditorialStyleProfile) -> str:
    alias = profile.venue_aliases.get(_key(venue))
    if alias:
        return alias

    cleaned = venue
    if city:
        escaped = re.escape(_clean(city))
        cleaned = re.sub(
            rf"\s*,?\s*{escaped}(?:\s*,\s*(?:WA|Washington))?(?:\s+\d{{5}})?\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" ,")

    if _ADDRESS_RE.search(cleaned):
        cleaned = cleaned.split(",", 1)[0].strip()
    return cleaned


def _display_title(
    title: str,
    venue: str,
    category: str | None,
    profile: EditorialStyleProfile,
) -> str:
    cleaned = title
    for prefix in sorted(profile.strip_prefixes, key=len, reverse=True):
        if cleaned.casefold().startswith(prefix.casefold()):
            cleaned = cleaned[len(prefix):].lstrip(" :-–—")
            break

    if profile.strip_terminal_date:
        cleaned = _TERMINAL_DATE_RE.sub("", cleaned).rstrip(" :-–—")

    if profile.deconflict_title_venue and venue:
        escaped = re.escape(venue)
        cleaned = re.sub(
            rf"\s+(?:at|@)\s+{escaped}\s*[!.,]*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

    if _key(category) == _MUSIC_CATEGORY:
        cleaned = _canonicalize_music_title(cleaned)

    return _clean(cleaned).strip(" !,|:-–—") or title


def _canonicalize_music_title(title: str) -> str:
    """Reduce promotional music copy to the performer billing."""
    cleaned = _MUSIC_LEADING_PROMO_RE.sub("", title).strip()
    cleaned = _MUSIC_PROMO_SENTENCE_RE.sub("", cleaned).strip()
    cleaned = _MUSIC_LIVE_VENUE_SUFFIX_RE.sub("", cleaned).strip()

    action_match = _MUSIC_ACTION_SUFFIX_RE.match(cleaned)
    if action_match:
        cleaned = action_match.group(1).strip()

    cleaned = re.sub(r"\s+(?:featuring|feat\.?|w/)\s+", " / ", cleaned, flags=re.IGNORECASE)
    return cleaned


def _key(value: Any) -> str:
    return _clean(value).casefold()


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip())
