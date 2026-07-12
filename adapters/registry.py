"""Configuration-backed source adapter registry.

Attempt_20 established the adapter manifest. Attempt_36 moves source enablement,
priority, status, and paths into one declarative registry while preserving the
legacy ``AVAILABLE_ADAPTERS`` mapping for existing callers.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from adapters.contract import AdapterManifest


DEFAULT_SOURCE_REGISTRY = Path("config/source_registry.json")


@dataclass(frozen=True)
class AdapterInfo(AdapterManifest):
    """Metadata and operating policy for one supported source adapter."""

    enabled: bool = True
    priority: int = 0


@dataclass(frozen=True)
class SourceRegistry:
    """Stable source inventory loaded from configuration."""

    adapters: dict[str, AdapterInfo]
    registry_version: int = 1

    @classmethod
    def load(cls, path: Path = DEFAULT_SOURCE_REGISTRY) -> "SourceRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("sources")
        if not isinstance(rows, list) or not rows:
            raise ValueError("source registry requires a non-empty sources list")

        adapters: dict[str, AdapterInfo] = {}
        for row in rows:
            adapter = _adapter_from_row(row)
            if adapter.source_name in adapters:
                raise ValueError(f"duplicate source registry entry: {adapter.source_name}")
            adapters[adapter.source_name] = adapter

        return cls(
            adapters=adapters,
            registry_version=int(payload.get("registry_version", 1)),
        )

    def get(self, source_name: str) -> AdapterInfo:
        try:
            return self.adapters[source_name]
        except KeyError as exc:
            known = ", ".join(sorted(self.adapters))
            raise KeyError(
                f"Unknown source adapter: {source_name}. Known adapters: {known}"
            ) from exc

    def names(self, *, enabled_only: bool = False) -> list[str]:
        adapters = self.enabled() if enabled_only else list(self.adapters.values())
        return [adapter.source_name for adapter in _ordered(adapters)]

    def enabled(self) -> list[AdapterInfo]:
        return _ordered(adapter for adapter in self.adapters.values() if adapter.enabled)


def _adapter_from_row(row: Any) -> AdapterInfo:
    if not isinstance(row, dict):
        raise ValueError("source registry entries must be objects")

    required = ("source_name", "adapter_package", "status", "fixture_path")
    missing = [field for field in required if not str(row.get(field) or "").strip()]
    if missing:
        raise ValueError(f"source registry entry missing fields: {missing}")

    raw_fixture = row.get("raw_fixture_path")
    return AdapterInfo(
        source_name=str(row["source_name"]).strip(),
        adapter_package=str(row["adapter_package"]).strip(),
        status=str(row["status"]).strip(),
        fixture_path=Path(str(row["fixture_path"]).strip()),
        raw_fixture_path=Path(str(raw_fixture).strip()) if raw_fixture else None,
        notes=str(row.get("notes") or "").strip() or None,
        enabled=bool(row.get("enabled", True)),
        priority=int(row.get("priority", 0)),
    )


def _ordered(adapters) -> list[AdapterInfo]:
    return sorted(adapters, key=lambda item: (-item.priority, item.source_name.casefold()))


SOURCE_REGISTRY = SourceRegistry.load()

# Backwards-compatible executable manifest. Planned sources remain visible through
# SOURCE_REGISTRY but do not appear here until a harvester implementation exists.
AVAILABLE_ADAPTERS: dict[str, AdapterInfo] = {
    name: adapter
    for name, adapter in SOURCE_REGISTRY.adapters.items()
    if adapter.status != "planned"
}


def get_adapter(source_name: str) -> AdapterInfo:
    return SOURCE_REGISTRY.get(source_name)


def list_source_names() -> list[str]:
    """Return implemented source names in the legacy alphabetical order."""
    return sorted(AVAILABLE_ADAPTERS)


def list_enabled_source_names() -> list[str]:
    """Return enabled production source names in priority order."""
    return SOURCE_REGISTRY.names(enabled_only=True)


def list_active_adapters() -> list[AdapterInfo]:
    """Return enabled active adapters for normal fixture-backed runs."""
    return [
        adapter
        for adapter in SOURCE_REGISTRY.enabled()
        if adapter.status == "active"
    ]
