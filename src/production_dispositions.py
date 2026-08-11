"""Apply explicit Captain-approved production dispositions to exact source records."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.geography import enrich_event_geography
from src.intelligence import attach_intelligence


DEFAULT_PRODUCTION_DISPOSITIONS_PATH = Path("config/production_dispositions.json")
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProductionDispositions:
    mission_id: str
    week_start: str
    resolutions: tuple[dict[str, Any], ...]
    exclusions: tuple[dict[str, Any], ...]
    selector_audit: tuple[dict[str, Any], ...] = field(
        default=(), init=False, repr=False, compare=False
    )

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
        self._validate_selector_roles()
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
                    if "start_time" in disposition:
                        copied["start_time"] = disposition["start_time"]
                        copied["end_time"] = disposition.get("end_time")
                    geography_correction = disposition.get("geography_correction")
                    if geography_correction:
                        copied = _apply_geography_correction(copied, geography_correction)
                    copied["production_disposition_cohort"] = disposition["cohort"]
                else:
                    copied["captain_disposition"] = "EXCLUDE"
                    copied["captain_disposition_reason"] = disposition["reason"]
                    copied["production_disposition_cohort"] = disposition["cohort"]
                copied["intelligence"] = attach_intelligence(
                    {"intelligence": copied.get("intelligence") or {}},
                    "captain_disposition",
                    {"mission_id": self.mission_id, "action": action, "cohort": disposition["cohort"], "evidence": disposition["evidence"], "evidence_url": disposition.get("evidence_url"), "evidence_authority": disposition.get("evidence_authority"), "detail": disposition.get("detail")},
                    1.0,
                    disposition.get("decision_reason", "captain_approved_preserved_evidence"),
                )["intelligence"]
            output.append(copied)
        self._require_all_selectors(matched)
        return self._attach_selector_audit(output, matched)

    def _matches(self, event: Mapping[str, Any]):
        for action, cohorts in (("RESOLVE", self.resolutions), ("EXCLUDE", self.exclusions)):
            for cohort_index, cohort in enumerate(cohorts):
                for selector_index, selector in enumerate(cohort.get("selectors", ())):
                    if _matches_selector(event, selector):
                        yield action, cohort_index, selector_index, cohort

    def _require_all_selectors(self, matched: set[tuple[str, int, int]]) -> None:
        expected = {
            (action, cohort_index, selector_index)
            for action, cohorts in (("RESOLVE", self.resolutions), ("EXCLUDE", self.exclusions))
            for cohort_index, cohort in enumerate(cohorts)
            for selector_index, selector in enumerate(cohort.get("selectors", ()))
            if _selector_role(selector) == "required"
        }
        missing = expected - matched
        if missing:
            raise ValueError(f"Captain disposition selectors did not match production input: {sorted(missing)}")

    def _validate_selector_roles(self) -> None:
        for action, cohorts in (("RESOLVE", self.resolutions), ("EXCLUDE", self.exclusions)):
            for cohort_index, cohort in enumerate(cohorts):
                roles = tuple(
                    _selector_role(selector)
                    for selector in cohort.get("selectors", ())
                )
                if action == "EXCLUDE" and any(
                    role not in {"required", "safe_absence"} for role in roles
                ):
                    raise ValueError(
                        "EXCLUDE Captain disposition selectors must be required or "
                        f"safe_absence: {cohort_index}"
                    )
                if action == "RESOLVE" and any(
                    role not in {"required", "suppressed"} for role in roles
                ):
                    raise ValueError(
                        "RESOLVE Captain disposition selectors must be required or "
                        f"suppressed: {cohort_index}"
                    )
                if action == "RESOLVE" and "required" not in roles:
                    raise ValueError(
                        f"RESOLVE Captain disposition requires a surviving selector: {cohort_index}"
                    )
                if action == "RESOLVE" and not any(
                    field in cohort for field in ("title", "start_time", "geography_correction")
                ):
                    raise ValueError(
                        f"RESOLVE Captain disposition requires a correction: {cohort_index}"
                    )
                if action == "RESOLVE" and "end_time" in cohort and "start_time" not in cohort:
                    raise ValueError(
                        f"RESOLVE Captain disposition cannot set end_time without start_time: {cohort_index}"
                    )

    def _attach_selector_audit(
        self,
        events: list[dict[str, Any]],
        matched: set[tuple[str, int, int]],
    ) -> list[dict[str, Any]]:
        audits: dict[str, dict[str, Any]] = {}
        for action, cohorts in (("RESOLVE", self.resolutions), ("EXCLUDE", self.exclusions)):
            for cohort_index, cohort in enumerate(cohorts):
                selectors = tuple(cohort.get("selectors", ()))
                audited_role = "suppressed" if action == "RESOLVE" else "safe_absence"
                if not any(_selector_role(selector) == audited_role for selector in selectors):
                    continue
                selector_status = []
                for selector_index, selector in enumerate(selectors):
                    role = _selector_role(selector)
                    was_matched = (action, cohort_index, selector_index) in matched
                    if action == "EXCLUDE" and was_matched:
                        status = "matched_and_excluded"
                    elif role in {"suppressed", "safe_absence"} and not was_matched:
                        status = "absent"
                    elif role == "suppressed":
                        status = "matched_and_suppressed"
                    else:
                        status = "matched" if was_matched else "missing"
                    selector_status.append({
                        "selector_index": selector_index,
                        "role": role,
                        "status": status,
                        "source": selector.get("source"),
                        "source_event_id": selector.get("source_event_id"),
                    })
                audit = {
                    "mission_id": self.mission_id,
                    "action": action,
                    "cohort": cohort["cohort"],
                    "selectors": selector_status,
                }
                audits[str(cohort["cohort"])] = audit
                if action == "EXCLUDE":
                    for item in selector_status:
                        _LOGGER.warning(
                            "captain_exclude_selector_audit mission_id=%s cohort=%s "
                            "selector_index=%s source=%s source_event_id=%s status=%s",
                            self.mission_id,
                            cohort["cohort"],
                            item["selector_index"],
                            item["source"],
                            item["source_event_id"],
                            item["status"],
                        )

        object.__setattr__(self, "selector_audit", tuple(audits.values()))

        audited: list[dict[str, Any]] = []
        for event in events:
            cohort = str(event.get("production_disposition_cohort") or "")
            audit = audits.get(cohort)
            if audit is None:
                audited.append(event)
                continue
            audited.append(attach_intelligence(
                event,
                "captain_disposition_selector_audit",
                audit,
                1.0,
                "captain_selector_status_recorded",
            ))
        return audited


def _matches_selector(event: Mapping[str, Any], selector: Mapping[str, Any]) -> bool:
    for field in ("source", "source_event_id", "title", "start_date"):
        if field in selector and _clean(event.get(field)) != _clean(selector.get(field)):
            return False
    venue_contains = _clean(selector.get("venue_contains"))
    return not venue_contains or venue_contains in _clean(event.get("venue"))


def _selector_role(selector: Mapping[str, Any]) -> str:
    role = str(selector.get("role") or "required").strip().casefold()
    if role not in {"required", "suppressed", "safe_absence"}:
        raise ValueError(f"unsupported Captain disposition selector role: {role!r}")
    return role


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _identity(event: Mapping[str, Any]) -> str:
    return f"{event.get('source')}:{event.get('source_event_id')}:{event.get('title')}"


def _apply_geography_correction(
    event: dict[str, Any], correction: Mapping[str, Any]
) -> dict[str, Any]:
    required = {"venue", "city", "state", "evidence_basis"}
    missing = sorted(field for field in required if not _clean(correction.get(field)))
    if missing:
        raise ValueError(f"Captain geography correction missing fields: {missing}")

    copied = dict(event)
    copied["venue"] = str(correction["venue"]).strip()
    copied["city"] = str(correction["city"]).strip()
    copied["state"] = str(correction["state"]).strip()
    copied["display_venue"] = copied["venue"]
    copied["display_city"] = copied["city"]
    copied["venue_presentation_reason"] = "captain_corrected_preserved_event_description"
    copied = enrich_event_geography(copied)
    copied = attach_intelligence(
        copied,
        "captain_geography_correction",
        {
            "venue": copied["venue"],
            "city": copied["city"],
            "state": copied["state"],
            "evidence_basis": str(correction["evidence_basis"]).strip(),
            "resulting_region": copied["geo_region"],
            "resulting_scope": copied["geo_scope"],
        },
        1.0,
        "captain_approved_event_description_geography",
    )
    return copied
