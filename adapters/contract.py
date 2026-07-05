"""Shared source adapter contract.

Attempt_20 formalizes the adapter boundary without changing the canonical
Event schema, publisher, resolver, or pipeline spine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


CanonicalEvent = dict[str, Any]


@runtime_checkable
class SourceAdapter(Protocol):
    """Protocol implemented by source adapters that parse raw source content."""

    source_name: str
    status: str

    def parse(self, content: str) -> list[CanonicalEvent]:
        """Parse raw source content into canonical event dictionaries."""


@dataclass(frozen=True)
class AdapterManifest:
    """Declarative metadata for one source adapter."""

    source_name: str
    adapter_package: str
    status: str
    fixture_path: Path
    raw_fixture_path: Path | None = None
    notes: str | None = None
