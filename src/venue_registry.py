"""Deterministic venue registry import, matching, and enrichment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable


_SPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MCL_PAREN_RE = re.compile(r"^mid[- ]columbia librar(?:y|ies)\s*\(([^)]+)\)$", re.IGNORECASE)
_RICHLAND_LIBRARY_ROOMS = {
    "children s department",
    "story circle",
    "doris roberts gallery",
    "collaboratory",
    "the lawn",
    "conference room a",
    "conference room b",
    "conference rooms a and b",
    "children s department the lawn",
    "children s department collaboratory",
    "children s department collaboratory the lawn",
    "conference rooms a and b doris roberts gallery",
}


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
    method: str | None = None
    detail: str | None = None


class VenueRegistry:
    def __init__(self, records: Iterable[VenueRecord]):
        self.records = tuple(records)
        alias_map: dict[str, list[VenueRecord]] = {}
        address_map: dict[str, list[VenueRecord]] = {}
        street_map: dict[str, list[VenueRecord]] = {}

        for record in self.records:
            for alias in record.aliases():
                key = normalize_venue_key(alias)
                if key:
                    alias_map.setdefault(key, []).append(record)
            if record.address:
                address_key = normalize_address_key(record.address)
                street_key = normalize_street_key(record.address)
                if address_key:
                    address_map.setdefault(address_key, []).append(record)
                if street_key:
                    street_map.setdefault(street_key, []).append(record)

        self._alias_map = {key: tuple(values) for key, values in alias_map.items()}
        self._address_map = {key: tuple(values) for key, values in address_map.items()}
        self._street_map = {key: tuple(values) for key, values in street_map.items()}

    @staticmethod
    def _record_identity(record: VenueRecord) -> tuple[str, ...]:
        if record.place_id:
            return ("place_id", record.place_id)
        if record.address:
            return (
                "address_name",
                normalize_address_key(record.address),
                normalize_venue_key(record.canonical_name),
            )
        return (
            "record",
            normalize_venue_key(record.venue_name),
            normalize_venue_key(record.canonical_name),
        )

    @staticmethod
    def _record_quality(record: VenueRecord) -> tuple[int, int, int, int, int]:
        return (
            int(bool(record.official_name)),
            int(bool(record.place_id)),
            int(bool(record.address)),
            int(bool(record.website)),
            len(record.canonical_name),
        )

    @classmethod
    def _collapse_equivalent(cls, candidates: tuple[VenueRecord, ...]) -> tuple[VenueRecord, ...]:
        grouped: dict[tuple[str, ...], list[VenueRecord]] = {}
        for record in candidates:
            grouped.setdefault(cls._record_identity(record), []).append(record)

        representatives = [
            max(group, key=cls._record_quality)
            for group in grouped.values()
        ]
        return tuple(representatives)

    @classmethod
    def _resolve_candidates(
        cls,
        candidates: tuple[VenueRecord, ...],
        *,
        method: str,
        detail: str | None = None,
    ) -> VenueMatch:
        unique = cls._collapse_equivalent(candidates)
        if not unique:
            return VenueMatch(status="unknown")
        if len(unique) > 1:
            return VenueMatch(status="ambiguous", candidates=unique, method=method, detail=detail)
        return VenueMatch(status="matched", record=unique[0], candidates=unique, method=method, detail=detail)

    def match(self, venue_name: str | None) -> VenueMatch:
        key = normalize_venue_key(venue_name or "")
        if not key:
            return VenueMatch(status="missing")
        return self._resolve_candidates(self._alias_map.get(key, ()), method="alias")

    def match_event(self, event: dict[str, Any]) -> VenueMatch:
        venue_name = str(event.get("venue") or "").strip()
        key = normalize_venue_key(venue_name)
        if not key:
            return VenueMatch(status="missing")

        direct = self._resolve_candidates(self._alias_map.get(key, ()), method="alias")
        if direct.status != "unknown":
            return direct

        source = str(event.get("source") or "")
        if source == "RichlandLibrary" and key in _RICHLAND_LIBRARY_ROOMS:
            parent = self._resolve_candidates(
                self._alias_map.get(normalize_venue_key("Richland Public Library"), ()),
                method="parent_room",
                detail=venue_name,
            )
            if parent.status != "unknown":
                return parent

        parenthetical = _MCL_PAREN_RE.match(venue_name)
        if parenthetical:
            branch = parenthetical.group(1).strip()
            rewritten = f"{branch} Mid-Columbia Library"
            branch_match = self._resolve_candidates(
                self._alias_map.get(normalize_venue_key(rewritten), ()),
                method="branch_rewrite",
                detail=venue_name,
            )
            if branch_match.status != "unknown":
                return branch_match

        if key == normalize_venue_key("Mid-Columbia Library"):
            city = str(event.get("city") or "").strip()
            if city:
                rewritten = f"{city} Mid-Columbia Library"
                city_match = self._resolve_candidates(
                    self._alias_map.get(normalize_venue_key(rewritten), ()),
                    method="city_branch",
                    detail=venue_name,
                )
                if city_match.status != "unknown":
                    return city_match

        if key == normalize_venue_key("Richland Library"):
            richland = self._resolve_candidates(
                self._alias_map.get(normalize_venue_key("Richland Public Library"), ()),
                method="known_alias",
                detail=venue_name,
            )
            if richland.status != "unknown":
                return richland

        address = str(event.get("address") or "").strip()
        if address:
            exact = self._resolve_candidates(
                self._address_map.get(normalize_address_key(address), ()),
                method="address",
                detail=address,
            )
            if exact.status != "unknown":
                return exact
            street_key = normalize_street_key(address)
            if street_key:
                street = self._resolve_candidates(
                    self._street_map.get(street_key, ()),
                    method="street_address",
                    detail=address,
                )
                if street.status != "unknown":
                    return street

        # Some adapters put a bare street address in the venue field.
        street_key = normalize_street_key(venue_name)
        if street_key and any(char.isdigit() for char in venue_name):
            street = self._resolve_candidates(
                self._street_map.get(street_key, ()),
                method="venue_as_address",
                detail=venue_name,
            )
            if street.status != "unknown":
                return street

        return VenueMatch(status="unknown")

    def enrich_event(self, event: dict[str, Any]) -> tuple[dict[str, Any], VenueMatch]:
        copied = dict(event)
        match = self.match_event(copied)
        if match.status != "matched" or match.record is None:
            return copied, match

        record = match.record
        original_venue = str(copied.get("venue") or "").strip()
        copied["venue"] = record.canonical_name
        if match.method == "parent_room" and original_venue:
            copied.setdefault("venue_detail", original_venue)
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


def normalize_address_key(value: str) -> str:
    return normalize_venue_key(value.replace("united states", "").replace("usa", ""))


def normalize_street_key(value: str) -> str:
    first_segment = value.split(",", 1)[0]
    key = normalize_venue_key(first_segment)
    return key if any(char.isdigit() for char in key) else ""
