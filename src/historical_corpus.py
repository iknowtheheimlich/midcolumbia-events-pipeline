"""Build deterministic knowledge artifacts from the historical Reddit corpus.

This module is intentionally separate from the live publishing pipeline. Historical rows
teach registries and regression fixtures; they never become live events automatically.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
import csv
import json
from pathlib import Path
import re
from typing import Any, Iterable

from src.url_canonicalizer import canonicalize_url

_MARKDOWN_LINK_RE = re.compile(r"^\s*\[([^\]]+)\]\((.+)\)\s*$")
_RELATION_RE = re.compile(r"^\s*(.*?)\s*\(https?://[^)]+\)\s*$")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class CorpusBuildResult:
    row_count: int
    venues: list[dict[str, Any]]
    hosts: list[dict[str, Any]]
    artist_candidates: list[dict[str, Any]]
    recurring_patterns: list[dict[str, Any]]

    def summary(self) -> dict[str, int]:
        return {
            "historical_rows": self.row_count,
            "unique_venues": len(self.venues),
            "unique_hosts": len(self.hosts),
            "artist_candidates": len(self.artist_candidates),
            "recurring_families": len(self.recurring_patterns),
        }


def load_historical_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def build_historical_corpus(rows: Iterable[dict[str, Any]]) -> CorpusBuildResult:
    materialized = [dict(row) for row in rows]
    return CorpusBuildResult(
        row_count=len(materialized),
        venues=_build_entities(materialized, "Venue Reddit Combo", "🌆 Ultimate Venues", "venue"),
        hosts=_build_entities(materialized, "Host Reddit Combo", "Host", "host"),
        artist_candidates=_build_artist_candidates(materialized),
        recurring_patterns=_build_recurring_patterns(materialized),
    )


def write_historical_corpus(result: CorpusBuildResult, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "venues": result.venues,
        "hosts": result.hosts,
        "artist_candidates": result.artist_candidates,
        "recurring_patterns": result.recurring_patterns,
        "summary": result.summary(),
    }
    paths: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = output_dir / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths[name] = path
    return paths


def _build_entities(
    rows: list[dict[str, Any]],
    combo_field: str,
    relation_field: str,
    entity_type: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        combo_name, combo_url = _parse_markdown_link(row.get(combo_field))
        relation_name = _parse_relation_name(row.get(relation_field))
        name = combo_name or relation_name
        if not name:
            continue
        key = _key(name)
        item = grouped.setdefault(
            key,
            {
                "entity_type": entity_type,
                "canonical_name": combo_name or relation_name,
                "website": canonicalize_url(combo_url),
                "aliases": set(),
                "occurrences": 0,
                "first_seen": None,
                "last_seen": None,
                "provenance": "historical_reddit_corpus",
                "confidence": 0.95 if combo_name and combo_url else 0.80,
            },
        )
        for alias in (combo_name, relation_name):
            if alias:
                item["aliases"].add(_clean(alias))
        if combo_url and not item.get("website"):
            item["website"] = canonicalize_url(combo_url)
        item["occurrences"] += 1
        _update_seen(item, row.get("Date"))

    result = []
    for item in grouped.values():
        item["aliases"] = sorted(item["aliases"], key=str.casefold)
        result.append(item)
    return sorted(result, key=lambda item: item["canonical_name"].casefold())


def _build_artist_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    samples: dict[str, set[str]] = defaultdict(set)
    first_seen: dict[str, str | None] = {}
    last_seen: dict[str, str | None] = {}
    patterns = (
        re.compile(r"\b(?:live music|music)\s+(?:with|by|feat\.?|featuring)\s+(.+)$", re.I),
        re.compile(r"\b(?:concert|performance)\s+(?:with|by|feat\.?|featuring)\s+(.+)$", re.I),
        re.compile(r"^(.+?)\s+(?:live|in concert)$", re.I),
    )
    for row in rows:
        title = _clean(row.get("Event Name"))
        if not title:
            continue
        candidate = None
        for pattern in patterns:
            match = pattern.search(title)
            if match:
                candidate = _clean(match.group(1))
                break
        if not candidate or len(candidate) < 2:
            continue
        key = _key(candidate)
        counts[key] += 1
        samples[key].add(title)
        seen = _date_iso(row.get("Date"))
        if seen:
            first_seen[key] = min(filter(None, [first_seen.get(key), seen])) if first_seen.get(key) else seen
            last_seen[key] = max(filter(None, [last_seen.get(key), seen])) if last_seen.get(key) else seen

    result = []
    for key, count in counts.items():
        canonical = sorted(samples[key], key=len)[0]
        # Recover only the extracted tail, not the full sample title.
        extracted = next(
            (_clean(pattern.search(canonical).group(1)) for pattern in patterns if pattern.search(canonical)),
            canonical,
        )
        result.append(
            {
                "candidate_name": extracted,
                "occurrences": count,
                "first_seen": first_seen.get(key),
                "last_seen": last_seen.get(key),
                "sample_titles": sorted(samples[key])[:5],
                "provenance": "historical_title_inference",
                "confidence": 0.70,
                "needs_review": True,
            }
        )
    return sorted(result, key=lambda item: (-item["occurrences"], item["candidate_name"].casefold()))


def _build_recurring_patterns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        family = _parse_relation_name(row.get("Generated From"))
        if family:
            grouped[_key(family)].append({**row, "_family": family})

    result = []
    for family_rows in grouped.values():
        family = family_rows[0]["_family"]
        weekdays = Counter(_weekday(row.get("Date")) for row in family_rows if _weekday(row.get("Date")))
        times = Counter(_clean(row.get("Time, Price, Notes")) for row in family_rows if _clean(row.get("Time, Price, Notes")))
        venues = Counter(
            (_parse_markdown_link(row.get("Venue Reddit Combo"))[0] or _parse_relation_name(row.get("🌆 Ultimate Venues")))
            for row in family_rows
        )
        venues.pop(None, None)
        dates = sorted(filter(None, (_date_iso(row.get("Date")) for row in family_rows)))
        result.append(
            {
                "family": family,
                "occurrences": len(family_rows),
                "typical_weekday": weekdays.most_common(1)[0][0] if weekdays else None,
                "weekday_distribution": dict(sorted(weekdays.items())),
                "typical_time": times.most_common(1)[0][0] if times else None,
                "time_distribution": dict(times.most_common()),
                "typical_venue": venues.most_common(1)[0][0] if venues else None,
                "venue_distribution": dict(venues.most_common()),
                "first_seen": dates[0] if dates else None,
                "last_seen": dates[-1] if dates else None,
                "provenance": "historical_reddit_corpus",
                "confidence": _pattern_confidence(weekdays, times, venues),
            }
        )
    return sorted(result, key=lambda item: item["family"].casefold())


def _pattern_confidence(*counters: Counter[str]) -> float:
    scores = []
    for counter in counters:
        total = sum(counter.values())
        if total:
            scores.append(counter.most_common(1)[0][1] / total)
    return round(sum(scores) / len(scores), 3) if scores else 0.0


def _update_seen(item: dict[str, Any], value: Any) -> None:
    seen = _date_iso(value)
    if not seen:
        return
    item["first_seen"] = min(item["first_seen"], seen) if item["first_seen"] else seen
    item["last_seen"] = max(item["last_seen"], seen) if item["last_seen"] else seen


def _parse_markdown_link(value: Any) -> tuple[str | None, str | None]:
    text = _clean(value)
    if not text:
        return None, None
    match = _MARKDOWN_LINK_RE.match(text)
    return (_clean(match.group(1)), match.group(2).strip()) if match else (text, None)


def _parse_relation_name(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    match = _RELATION_RE.match(text)
    return _clean(match.group(1)) if match else text


def _date_iso(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _weekday(value: Any) -> str | None:
    iso = _date_iso(value)
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%A") if iso else None


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip())


def _key(value: Any) -> str:
    return _clean(value).casefold()
