"""Apply explicit Captain-approved production dispositions to exact source records."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.intelligence import attach_intelligence


DEFAULT_PRODUCTION_DISPOSITIONS_PATH = Path("config/production_dispositions.json")


@dataclass(frozen=True)
class ProductionDispositions:
    mission_id: str
    week_start: str
    resolutions: tuple[dict[str, Any], ...]
    exclusions: tuple[dict[str, Any], ...]

    @classmethod
    def load(cls, week_start: str, path: Path = DEFAULT_PRODUCTION_DISPOSITIONS_PATH) -> "ProductionDispositions | None":
        payload = json.loads(path.read_text(encoding="utf-8"))
        matches = [row for row in payload.get("missions", []) if row.get("week_start") == week_start]
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError(f"multiple production disposition sets for week {week_start}")
        row = matches[0]
        return cls(str(row["mission_id"]), week_start, tuple(row.get("resolutions", ())), tuple(row.get("exclusions", ())))

    def apply(self, events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        matched: set[tuple[str, int, int]] = set()
        for event in events:
            copied = dict(event)
            matches = list(self._matches(copied))
            if len(matches) > 1:
                raise ValueError(f"multiple Captain dispositions match {_identity(copied)}")
            if matches:
                action, cohort_index, selector_index, disposition = matches[0]
                matched.add((action, cohort_index, selector_index))
                if action == "RESOLVE":
                    if disposition.get("title"):
                        copied["title"] = disposition["title"]
                    copied["start_time"] = disposition["start_time"]
                    copied["end_time"] = disposition.get("end_time")
                else:
                    copied["captain_disposition"] = "EXCLUDE"
                    copied["captain_disposition_reason"] = disposition["reason"]
                copied["intelligence"] = attach_intelligence(
                    {"intelligence": copied.get("intelligence") or {}},
                    "captain_disposition",
                    {"mission_id": self.mission_id, "action": action, "cohort": disposition["cohort"], "evidence": disposition["evidence"], "evidence_url": disposition.get("evidence_url"), "evidence_authority": disposition.get("evidence_authority"), "detail": disposition.get("detail")},
                    1.0,
                    disposition.get("decision_reason", "captain_approved_preserved_evidence"),
                )["intelligence"]
            output.append(copied)
        self._require_all_selectors(matched)
        return output

    def _matches(self, event: Mapping[str, Any]):
        for action, cohorts in (("RESOLVE", self.resolutions), ("EXCLUDE", self.exclusions)):
            for cohort_index, cohort in enumerate(cohorts):
                for selector_index, selector in enumerate(cohort.get("selectors", ())):
                    if _matches_selector(event, selector):
                        yield action, cohort_index, selector_index, cohort

    def _require_all_selectors(self, matched: set[tuple[str, int, int]]) -> None:
        expected = {(action, cohort_index, selector_index) for action, cohorts in (("RESOLVE", self.resolutions), ("EXCLUDE", self.exclusions)) for cohort_index, cohort in enumerate(cohorts) for selector_index, _ in enumerate(cohort.get("selectors", ()))}
        missing = expected - matched
        if missing:
            raise ValueError(f"Captain disposition selectors did not match production input: {sorted(missing)}")


def _matches_selector(event: Mapping[str, Any], selector: Mapping[str, Any]) -> bool:
    for field in ("source", "source_event_id", "title", "start_date"):
        if field in selector and _clean(event.get(field)) != _clean(selector.get(field)):
            return False
    venue_contains = _clean(selector.get("venue_contains"))
    return not venue_contains or venue_contains in _clean(event.get("venue"))


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _identity(event: Mapping[str, Any]) -> str:
    return f"{event.get('source')}:{event.get('source_event_id')}:{event.get('title')}"
