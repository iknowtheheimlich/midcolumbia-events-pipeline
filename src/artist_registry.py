"""Canonical artist presentation metadata and review-safe enrichment."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

from src.url_canonicalizer import canonicalize_url

_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ArtistRecord:
    name: str
    website: str | None = None
    event_calendar: str | None = None
    genres: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    @property
    def publication_url(self) -> str | None:
        return canonicalize_url(self.website or self.event_calendar)


class ArtistRegistry:
    def __init__(self, records: Iterable[ArtistRecord] = ()):
        self._records: dict[str, ArtistRecord] = {}
        for record in records:
            for value in (record.name, *record.aliases):
                key = _key(value)
                if key:
                    self._records[key] = record

    @classmethod
    def from_json(cls, path: Path) -> "ArtistRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("artists", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("artist registry JSON must be a list or contain an artists list")
        records: list[ArtistRecord] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = _text(row.get("name") or row.get("Artist Name") or row.get("Clean Artist"))
            if not name:
                continue
            aliases = row.get("aliases") or []
            genres = row.get("genres") or row.get("Genre") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            if isinstance(genres, str):
                genres = [genres]
            records.append(
                ArtistRecord(
                    name=name,
                    website=_optional(row.get("website") or row.get("Artist Website")),
                    event_calendar=_optional(row.get("event_calendar") or row.get("Event Calendar")),
                    genres=tuple(_text(value) for value in genres if _text(value)),
                    aliases=tuple(_text(value) for value in aliases if _text(value)),
                )
            )
        return cls(records)

    def resolve(self, value: Any) -> ArtistRecord | None:
        return self._records.get(_key(value))

    def enrich(self, event: dict[str, Any]) -> dict[str, Any]:
        result = dict(event)
        detected = _first_text(result, "artist", "performer", "music_artist")
        if not detected:
            return result
        record = self.resolve(detected)
        if record is None:
            reasons = list(result.get("presentation_review_reasons") or [])
            if "unresolved_artist" not in reasons:
                reasons.append("unresolved_artist")
            result["presentation_review_reasons"] = reasons
            result["detected_artist"] = detected
            return result
        result["artist"] = record.name
        result["artist_url"] = record.publication_url
        result["artist_registry_name"] = record.name
        if record.genres:
            result["artist_genres"] = list(record.genres)
        return result


def enrich_artists(events: Iterable[dict[str, Any]], registry: ArtistRegistry) -> list[dict[str, Any]]:
    return [registry.enrich(event) for event in events]


def _key(value: Any) -> str:
    return _SPACE_RE.sub(" ", _text(value)).casefold()


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _optional(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _first_text(event: dict[str, Any], *fields: str) -> str | None:
    for field in fields:
        value = _optional(event.get(field))
        if value:
            return value
    return None
