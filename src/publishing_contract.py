"""Publisher-independent publication contract for enriched events.

Attempt_33_PublishingContract

This module owns semantic category vocabulary, publication-target routing, and
compact time grammar. Renderers consume these decisions; they do not make them.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DEFAULT_PROFILE_PATH = Path("config/reddit_publishing_profile.json")
VALID_PUBLICATION_TARGETS = {"MAIN", "COMMUNITY", "BOTH", "SUPPRESS", "REVIEW"}

CATEGORY_ALIASES = {
    "live music": "Music/Comedy",
    "music & concerts": "Music/Comedy",
    "arts & theater": "Art/Theater",
    "food & drink": "Food & Drink",
    "winery events": "Restaurants/Bars/Wineries",
    "sports & recreation": "Sports",
    "annual events": "Festivals/Fair",
    "community events": "Events/Hangouts",
    "history & heritage": "Tours",
    "kids & family": "Community Programs",
    "kids and families": "Community Programs",
    "adult": "Community Programs",
    "all ages": "Community Programs",
    "all ages kids and families": "Community Programs",
    "middle school high school adult": "Community Programs",
    "high school adult": "Community Programs",
    "all ages middle school high school adult": "Community Programs",
    "middle school high school": "Community Programs",
    "all ages kids and families middle school high school adult": "Community Programs",
    "kids and families middle school": "Community Programs",
    "all ages adult": "Community Programs",
    "other": "Events/Hangouts",
}


@dataclass(frozen=True)
class PublishingProfile:
    """Configuration-backed publication policy."""

    category_order: tuple[str, ...]
    category_targets: dict[str, str]
    time_style: str = "compact"
    profile_version: int = 1

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PublishingProfile":
        order = tuple(str(value).strip() for value in payload.get("category_order", []) if str(value).strip())
        if not order:
            raise ValueError("publishing profile requires category_order")
        if len(set(order)) != len(order):
            raise ValueError("publishing profile category_order contains duplicates")

        targets: dict[str, str] = {}
        configured = payload.get("publication_targets", {})
        if not isinstance(configured, dict):
            raise ValueError("publishing profile publication_targets must be an object")
        for target, categories in configured.items():
            normalized_target = str(target).strip().upper()
            if normalized_target not in VALID_PUBLICATION_TARGETS:
                raise ValueError(f"invalid publication target: {target!r}")
            for category in categories or []:
                normalized_category = str(category).strip()
                if normalized_category in targets:
                    raise ValueError(f"category assigned to multiple publication targets: {normalized_category!r}")
                targets[normalized_category] = normalized_target

        missing = set(order).difference(targets)
        extra = set(targets).difference(order)
        if missing:
            raise ValueError(f"publishing profile categories missing targets: {sorted(missing)!r}")
        if extra:
            raise ValueError(f"publishing profile targets contain unknown categories: {sorted(extra)!r}")

        time_style = str(payload.get("time_style", "compact")).strip().casefold()
        if time_style != "compact":
            raise ValueError(f"unsupported time style: {time_style!r}")

        return cls(
            category_order=order,
            category_targets=targets,
            time_style=time_style,
            profile_version=int(payload.get("profile_version", 1)),
        )

    @classmethod
    def load(cls, path: Path = DEFAULT_PROFILE_PATH) -> "PublishingProfile":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def normalize_category(self, value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        text = value.strip()
        lookup = {category.casefold(): category for category in self.category_order}
        direct = lookup.get(text.casefold())
        if direct is not None:
            return direct
        alias = CATEGORY_ALIASES.get(text.casefold())
        return alias if alias in self.category_order else None

    def publication_target(self, category: str | None, explicit_target: str | None = None) -> str:
        if explicit_target and explicit_target.strip():
            target = explicit_target.strip().upper()
            if target not in VALID_PUBLICATION_TARGETS:
                return "REVIEW"
            return target
        normalized_category = self.normalize_category(category)
        if normalized_category is None:
            return "REVIEW"
        return self.category_targets[normalized_category]


def format_compact_time(value: str | None) -> str | None:
    """Convert canonical 24-hour time to compact Reddit grammar.

    Examples: 17:00 -> 5p, 10:30 -> 10:30a, 00:00 -> 12a.
    Non-canonical values pass through unchanged for backwards compatibility.
    """
    if not value:
        return None
    text = value.strip()
    parts = text.split(":")
    if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
        return text
    hour, minute = int(parts[0]), int(parts[1])
    if hour > 23 or minute > 59:
        return text
    suffix = "a" if hour < 12 else "p"
    display_hour = hour % 12 or 12
    return f"{display_hour}{suffix}" if minute == 0 else f"{display_hour}:{minute:02d}{suffix}"


def format_compact_range(start: str | None, end: str | None) -> str | None:
    """Render a compact time range without redundant suffixes.

    Examples: 5p-6p -> 5-6p, 10:30a-11a -> 10:30-11a,
    11a-1p remains 11a-1p because the suffix changes.
    """
    start_text = format_compact_time(start)
    end_text = format_compact_time(end)
    if not start_text and not end_text:
        return None
    if not start_text:
        return end_text
    if not end_text:
        return start_text
    if start_text[-1:] == end_text[-1:] and start_text[-1:] in {"a", "p"}:
        return f"{start_text[:-1]}-{end_text}"
    return f"{start_text}-{end_text}"
