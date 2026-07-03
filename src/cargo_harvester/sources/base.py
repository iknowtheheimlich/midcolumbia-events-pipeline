from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Protocol

from cargo_harvester.models import EventRecord

LogFn = Callable[[str], None]


@dataclass(frozen=True)
class SourceResult:
    source_name: str
    events: list[EventRecord]
    debug: list[dict] | None = None


class EventSource(Protocol):
    name: str

    async def harvest(self, city: str, start: date, end: date, headless: bool = True, log: LogFn | None = None) -> SourceResult:
        """Harvest events and return canonical EventRecord objects."""
        ...
