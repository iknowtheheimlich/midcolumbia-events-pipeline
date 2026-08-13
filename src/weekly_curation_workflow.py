"""Frozen-inventory boundary for staged Weekly Curation production runs."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from src.notion_weekly_curation import (
    CurationIntegrityError,
    NotionCurationClient,
    apply_captain_authority,
    curation_key,
    read_week,
    sync_week,
)
from src.publisher_editorial import EditorialEvent

WEEKLY_CURATION_DATABASE_URL = "https://app.notion.com/p/971914760da0416f970beea53a2b49a0"
WEEKLY_CURATION_DATA_SOURCE_ID = "c4d70d49-4009-4607-a003-9ccb2c302634"


def inventory_rows(events: Iterable[EditorialEvent]) -> list[dict[str, Any]]:
    rows=[]
    for event in events:
        item=event.to_dict()
        rows.append({
            "Date":event.start_date, "Start Time":event.display_start_time or "",
            "End Time":event.display_end_time or "", "Title":event.canonical_title or event.title,
            "Venue":event.display_venue, "City":event.display_city, "Source":event.source,
            "Source Event ID":event.source_event_id or "", "URL":event.publication_url,
            "Description":event.description or "", "Current Category":event.semantic_category or "",
            "Category Confidence":event.category_confidence, "Category Reason":event.category_reason or "",
            "Current Target":event.publication_target, "Current Disposition":event.publication_disposition,
            "Editorial Reason":event.editorial_reason or "", "Editorial Event":item,
        })
    return rows


def prepare_curation(client: NotionCurationClient, events: Iterable[EditorialEvent], *, week: str, run_id: str, inventory_path: Path, audit_path: Path) -> dict[str, Any]:
    rows=inventory_rows(events)
    keys=[curation_key(row,week) for row in rows]
    if len(keys)!=len(set(keys)): raise CurationIntegrityError("duplicate incoming Curation Keys")
    inventory_path.parent.mkdir(parents=True,exist_ok=True)
    payload={"week":week,"rows":rows}
    inventory_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    digest=_digest(payload)
    result=sync_week(client,rows,week=week,run_id=run_id)
    audit={"week":week,"run_id":run_id,"inventory_path":str(inventory_path),"inventory_sha256":digest,"inventory_count":len(rows),"database_url":WEEKLY_CURATION_DATABASE_URL,"data_source_id":client.data_source_id,"sync":result}
    audit_path.parent.mkdir(parents=True,exist_ok=True)
    audit_path.write_text(json.dumps(audit,indent=2,sort_keys=True),encoding="utf-8")
    return audit


def load_curated_editorial(client: NotionCurationClient, *, week: str, inventory_path: Path, audit_path: Path) -> list[EditorialEvent]:
    if not inventory_path.exists() or not audit_path.exists(): raise CurationIntegrityError("expected sync audit/inventory boundary is missing")
    payload=json.loads(inventory_path.read_text(encoding="utf-8")); audit=json.loads(audit_path.read_text(encoding="utf-8"))
    if payload.get("week")!=week or audit.get("week")!=week or audit.get("inventory_sha256")!=_digest(payload): raise CurationIntegrityError("inventory boundary does not match sync audit")
    rows=payload.get("rows") or []
    if audit.get("inventory_count")!=len(rows): raise CurationIntegrityError("inventory count does not match sync audit")
    expected={curation_key(row,week):row for row in rows}
    if len(expected)!=len(rows): raise CurationIntegrityError("duplicate inventory Curation Keys")
    curated=read_week(client,week); actual={row["Curation Key"]:row for row in curated}
    if set(actual)!=set(expected): raise CurationIntegrityError(f"row identity does not reconcile: missing={sorted(set(expected)-set(actual))} unexpected={sorted(set(actual)-set(expected))}")
    output=[]
    for key, source in expected.items():
        notion=actual[key]
        _validate_pipeline_identity(source,notion)
        final=apply_captain_authority(notion)
        base=EditorialEvent(**source["Editorial Event"])
        disposition=base.publication_disposition
        if final["Final Inclusion"]=="INCLUDE": disposition="AUTO_PUBLISH"
        elif final["Final Inclusion"]=="EXCLUDE": disposition="REJECT"
        output.append(replace(base,title=final["Event"],display_time=final["Final Time"],semantic_category=final["Final Category"] or None,category=final["Final Category"] or None,publication_target=final["Final Target"],publication_disposition=disposition,editorial_reason="captain_excluded_this_week" if disposition=="REJECT" and notion.get("Captain Include")=="EXCLUDE" else base.editorial_reason))
    return output


def _validate_pipeline_identity(source, notion):
    pairs=(("Title","Original Title"),("Date","Event Date"),("Source","Source"),("Source Event ID","Source Event ID"),("URL","Source URL"),("Venue","Venue"),("City","City"),("Current Category","Pipeline Category"),("Current Target","Pipeline Target"),("Current Disposition","Pipeline Disposition"))
    bad=[left for left,right in pairs if _norm(source.get(left))!=_norm(notion.get(right))]
    if bad: raise CurationIntegrityError(f"pipeline row identity differs for {source.get('Title')!r}: {bad}")


def _digest(payload): return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def _norm(value): return " ".join(str(value or "").strip().split())
