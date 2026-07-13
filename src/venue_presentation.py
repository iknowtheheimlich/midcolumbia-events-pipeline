"""Authoritative venue presentation derived from registry-enriched events.

Attempt_50_VenuePresentationProfile

Canonical venue identity remains untouched. This layer decides how a resolved venue is
shown to humans and gives every presentation consumer the same name, URL, and city.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


DEFAULT_PROFILE_PATH = Path("config/venue_presentation.json")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class VenuePresentation:
    canonical_name: str
    display_name: str
    display_url: str | None
    display_city: str | None
    suppress_city: bool = False
    short_name: str | None = None
    venue_type: str | None = None
    parent_display_name: str | None = None
    reason: str = "fallback"


@dataclass(frozen=True)
class VenuePresentationRule:
    display_name: str
    display_url: str | None = None
    display_city: str | None = None
    suppress_city: bool = False
    short_name: str | None = None
    parent_display_name: str | None = None


class VenuePresentationProfile:
    def __init__(self, rules: dict[str, VenuePresentationRule], profile_version: int = 1):
        self.rules = {_key(key): value for key, value in rules.items()}
        self.profile_version = profile_version

    @classmethod
    def load(cls, path: Path = DEFAULT_PROFILE_PATH) -> "VenuePresentationProfile":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rules = {
            _key(key): VenuePresentationRule(**value)
            for key, value in (payload.get("venues") or {}).items()
        }
        return cls(rules, int(payload.get("profile_version", 1)))

    def present(self, event: dict[str, Any]) -> VenuePresentation:
        canonical = _first_text(
            event,
            "venue_registry_name",
            "venue",
        ) or "Unknown Venue"
        candidates = [
            _first_text(event, "venue_registry_name"),
            _first_text(event, "venue"),
            _first_text(event, "parent_venue", "venue_parent"),
        ]
        rule = next((self.rules.get(_key(value)) for value in candidates if value and _key(value) in self.rules), None)

        if rule is not None:
            return VenuePresentation(
                canonical_name=canonical,
                display_name=rule.display_name,
                display_url=rule.display_url or _first_text(event, "venue_website"),
                display_city=rule.display_city or _first_text(event, "city"),
                suppress_city=rule.suppress_city,
                short_name=rule.short_name,
                venue_type=_first_text(event, "venue_type", "registry_venue_type"),
                parent_display_name=rule.parent_display_name,
                reason="profile_rule",
            )

        return VenuePresentation(
            canonical_name=canonical,
            display_name=canonical,
            display_url=_first_text(event, "venue_website"),
            display_city=_first_text(event, "city"),
            suppress_city=False,
            venue_type=_first_text(event, "venue_type", "registry_venue_type"),
            parent_display_name=_first_text(event, "parent_venue", "venue_parent"),
            reason="registry_fallback" if event.get("venue_registry_name") else "source_fallback",
        )


def present_event(
    event: dict[str, Any],
    profile: VenuePresentationProfile | None = None,
) -> VenuePresentation:
    return (profile or VenuePresentationProfile.load()).present(event)


def _key(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip()).casefold()


def _first_text(event: dict[str, Any], *fields: str) -> str | None:
    for field in fields:
        value = event.get(field)
        if value is None:
            continue
        text = _SPACE_RE.sub(" ", str(value).strip())
        if text:
            return text
    return None
