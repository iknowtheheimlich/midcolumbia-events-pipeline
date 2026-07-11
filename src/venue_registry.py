"""Deterministic venue registry import, matching, and enrichment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable


_SPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class VenueRecord:
    venue_name: str
    official_name: str | None = None
    address: str | None = None
    place_id: str | None = None
    plus_code: str | None = None
    website: str | None = None
    venue_type: str | None = None
    reddit_combo: str | None = None

    @property
    def canonical_name(self) -> str:
        return self.official_name or self.venue_name

    def aliases(self) -> set[str]:
        return {
            value
            for value in (self.venue_name, self.official_name, self.reddit_combo)
            if value and value.strip()
        }


@dataclass(frozen=True)
class VenueMatch:
    status: str
    record: VenueRecord | None = None
    candidates: tuple[VenueRecord, ...] = ()


class VenueRegistry:
    def __init__(self, records: Iterable[VenueRecord]):
        self.records = tuple(records)
        alias_map: dict[str, list[VenueRecord]] = {}
        for record in self.records:
            for alias in record.aliases():
                key = normalize_venue_key(alias)
                if key:
                    alias_map.setdefault(key, []).append(record)
        self._alias_map = {key: tuple(values) for key, values in alias_map.items()}

    def match(self, venue_name: str | None) -> VenueMatch:
        key = normalize_venue_key(venue_name or "")
        if not key:
            return VenueMatch(status="missing")
        candidates = self._alias_map.get(key, ())
        if not candidates:
            return VenueMatch(status="unknown")
        unique = tuple(dict.fromkeys(candidates))
        if len(unique) > 1:
            return VenueMatch(status="ambiguous", candidates=unique)
        return VenueMatch(status="matched", record=unique[0], candidates=unique)

    def enrich_event(self, event: dict[str, Any]) -> tuple[dict[str, Any], VenueMatch]:
        copied = dict(event)
        match = self.match(copied.get("venue"))
        if match.status != "matched" or match.record is None:
            return copied, match

        record = match.record
        copied["venue"] = record.canonical_name
        if record.place_id and not copied.get("venue_id"):
            copied["venue_id"] = record.place_id
        if record.address and not copied.get("address"):
            copied["address"] = record.address
        return copied, match

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(record) for record in sorted(self.records, key=lambda item: item.venue_name.casefold())]
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> "VenueRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(VenueRecord(**row) for row in payload)


def normalize_venue_key(value: str) -> str:
    text = value.casefold().replace("&", " and ")
    text = _NON_ALNUM_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()
