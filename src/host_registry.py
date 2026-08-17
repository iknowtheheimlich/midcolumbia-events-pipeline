"""Canonical host and performer presentation metadata.

Harvested events may identify an organizer, host, band, or performer. This registry
owns the public display name and destination URL used by publishers. Source URLs are
never allowed to overwrite curated host metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class HostRecord:
    name: str
    website: str | None = None
    event_calendar: str | None = None
    aliases: tuple[str, ...] = ()

    @property
    def publication_url(self) -> str | None:
        return self.website or self.event_calendar


class HostRegistry:
    def __init__(self, records: Iterable[HostRecord] = ()):
        self._records: dict[str, HostRecord] = {}
        for record in records:
            for value in (record.name, *record.aliases):
                key = _key(value)
                if key:
                    self._records[key] = record

    @classmethod
    def from_json(cls, path: Path) -> "HostRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("hosts", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("host registry JSON must be a list or contain a hosts list")
        records = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = _text(row.get("name") or row.get("Host Name") or row.get("Clean Host"))
            if not name:
                continue
            aliases = row.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            records.append(
                HostRecord(
                    name=name,
                    website=_optional(row.get("website") or row.get("Host Website")),
                    event_calendar=_optional(row.get("event_calendar") or row.get("Event Calendar")),
                    aliases=tuple(_text(value) for value in aliases if _text(value)),
                )
            )
        return cls(records)

    def resolve(self, value: Any) -> HostRecord | None:
        return self._records.get(_key(value))

    def enrich(self, event: dict[str, Any]) -> dict[str, Any]:
        result = dict(event)
        detected = _first_text(result, "organization", "organizer", "host", "performer", "artist")
        if not detected:
            return result
        record = self.resolve(detected)
        if record is None:
            result.setdefault("presentation_review_reasons", []).append("unresolved_host")
            result["detected_host"] = detected
            return result
        result["organization"] = record.name
        result["organization_url"] = record.publication_url
        result["host_registry_name"] = record.name
        return result


def enrich_hosts(events: Iterable[dict[str, Any]], registry: HostRegistry) -> list[dict[str, Any]]:
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
