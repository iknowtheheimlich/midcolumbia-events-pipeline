"""Build a deterministic review queue for missing curated presentation metadata."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class PresentationReviewItem:
    kind: str
    detected_name: str
    reason: str
    source: str
    event_title: str
    event_url: str
    venue: str | None = None
    city: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_presentation_review(events: Iterable[dict[str, Any]]) -> list[PresentationReviewItem]:
    items: list[PresentationReviewItem] = []
    seen: set[tuple[str, str, str]] = set()
    for event in events:
        reasons = event.get("presentation_review_reasons") or []
        if isinstance(reasons, str):
            reasons = [reasons]

        if not event.get("venue_registry_name"):
            reasons = [*reasons, "unresolved_venue"]

        for reason in reasons:
            if reason == "unresolved_host":
                kind = "HOST"
                detected = _text(event.get("detected_host"))
            elif reason == "unresolved_venue":
                kind = "VENUE"
                detected = _text(event.get("venue"))
            else:
                kind = "PRESENTATION"
                detected = _text(event.get("venue") or event.get("organization"))
            if not detected:
                continue
            key = (kind, detected.casefold(), str(reason))
            if key in seen:
                continue
            seen.add(key)
            items.append(
                PresentationReviewItem(
                    kind=kind,
                    detected_name=detected,
                    reason=str(reason),
                    source=_text(event.get("source")),
                    event_title=_text(event.get("title")),
                    event_url=_text(event.get("url")),
                    venue=_optional(event.get("venue")),
                    city=_optional(event.get("city")),
                )
            )
    return sorted(items, key=lambda item: (item.kind, item.detected_name.casefold(), item.reason))


def write_presentation_review(items: Iterable[PresentationReviewItem], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [item.to_dict() for item in items]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _optional(value: Any) -> str | None:
    text = _text(value)
    return text or None
