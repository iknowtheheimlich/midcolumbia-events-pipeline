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
from src.notion_weekly import _parse_reddit_combo
from src.publisher_editorial import EditorialEvent
from src.publishing_contract import PublishingProfile

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
            "Source Start Date":event.source_start_date or event.start_date,
            "Source End Date":event.source_end_date or event.end_date or event.start_date,
            "Occurrence Identity":event.occurrence_identity or "",
            "Source Time Evidence":json.dumps(event.source_time_evidence,sort_keys=True,separators=(",",":")),
        })
    return rows


def prepare_curation(client: NotionCurationClient, events: Iterable[EditorialEvent], *, week: str, run_id: str, inventory_path: Path, audit_path: Path, production_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    rows=inventory_rows(events)
    keys=[curation_key(row,week) for row in rows]
    if len(keys)!=len(set(keys)): raise CurationIntegrityError("duplicate incoming Curation Keys")
    inventory_path.parent.mkdir(parents=True,exist_ok=True)
    payload={"week":week,"rows":rows}
    inventory_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    digest=_digest(payload)
    result=sync_week(client,rows,week=week,run_id=run_id)
    audit={"week":week,"run_id":run_id,"inventory_path":str(inventory_path),"inventory_sha256":digest,"inventory_count":len(rows),"database_url":WEEKLY_CURATION_DATABASE_URL,"data_source_id":client.data_source_id,"sync":result,"production_evidence":production_evidence or {}}
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
    missing=sorted(set(expected)-set(actual)); extra=set(actual)-set(expected)
    retained_items=(audit.get("sync") or {}).get("retained_rows",[])
    retained={item.get("curation_key") for item in retained_items}
    if None in retained or len(retained)!=len(retained_items): raise CurationIntegrityError("retained-row audit contains missing or duplicate Curation Keys")
    unexpected=sorted(extra-retained); missing_retained=sorted(retained-extra)
    if missing or unexpected or missing_retained:
        raise CurationIntegrityError(f"row identity does not reconcile: missing={missing} unexpected={unexpected} missing_retained={missing_retained}")
    _validate_retained_rows(retained_items,actual)
    run_id=_norm(audit.get("run_id"))
    wrong_run=sorted(key for key in expected if _norm(actual[key].get("Pipeline Run ID"))!=run_id)
    if wrong_run: raise CurationIntegrityError(f"frozen rows have wrong Pipeline Run ID: {wrong_run}")
    profile=PublishingProfile.load()
    output=[]
    for key, source in expected.items():
        notion=actual[key]
        _validate_pipeline_identity(source,notion)
        final=apply_captain_authority(notion)
        base=EditorialEvent(**source["Editorial Event"])
        captain_category=_norm(notion.get("Captain Category"))
        captain_target=_norm(notion.get("Captain Target"))
        final_category=profile.normalize_category(final["Final Category"])
        if captain_target:
            final_target=profile.publication_target(final_category,captain_target)
        elif captain_category:
            final_target=profile.publication_target(final_category)
        else:
            final_target=profile.publication_target(final_category,notion.get("Pipeline Target"))
        disposition=base.publication_disposition
        if final["Final Inclusion"]=="INCLUDE": disposition="AUTO_PUBLISH"
        elif final["Final Inclusion"]=="EXCLUDE": disposition="REJECT"
        if disposition=="AUTO_PUBLISH" and (final_category is None or final_target not in {"MAIN","COMMUNITY"}):
            raise CurationIntegrityError(f"unresolved Captain decision for {source.get('Title')!r}: category={final_category!r} target={final_target!r}")
        changes={"title":final["Event"],"display_time":final["Final Time"],"semantic_category":final_category,"category":final_category,"publication_target":final_target,"publication_disposition":disposition,"editorial_reason":"captain_excluded_this_week" if disposition=="REJECT" and notion.get("Captain Include")=="EXCLUDE" else base.editorial_reason}
        description=_norm(notion.get("Captain Description Override"))
        if description: changes["description"]=description
        venue_relation=_norm(notion.get("Captains Venue Override"))
        if venue_relation:
            venue=_resolve_captain_venue(client,venue_relation)
            changes["display_venue"]=venue["name"]
            if venue["city"]: changes["display_city"]=venue["city"]
            if venue["url"]: changes["publication_url"]=venue["url"]
        output.append(replace(base,**changes))
    return output

def _resolve_captain_venue(client, relation_id):
    if "," in relation_id: raise CurationIntegrityError(f"Captain venue override is ambiguous: {relation_id}")
    venue=client.resolve_venue_override(relation_id)
    combo_name,combo_url,combo_city=_parse_reddit_combo(venue.get("Venue Reddit Combo") or "")
    name=combo_name or _norm(venue.get("Venue Name")); url=combo_url or _norm(venue.get("Venue URL")); city=combo_city
    if not name: raise CurationIntegrityError(f"Captain venue override {relation_id} lacks canonical presentation")
    return {"name":name,"url":url,"city":city}

def _validate_retained_rows(retained, actual):
    pairs=(("title","Original Title"),("event_date","Event Date"),("source","Source"),("source_event_id","Source Event ID"),("prior_pipeline_run_id","Pipeline Run ID"))
    for item in retained:
        row=actual[item["curation_key"]]
        bad=[live for audit,live in pairs if _norm(item.get(audit))!=_norm(row.get(live))]
        if bad:
            raise CurationIntegrityError(f"retained row differs from PREPARE audit for {item['curation_key']}: pipeline={bad}")


def _validate_pipeline_identity(source, notion):
    pairs=(("Title","Original Title"),("Date","Event Date"),("Source","Source"),("Source Event ID","Source Event ID"),("URL","Source URL"),("Venue","Venue"),("City","City"),("Source Start Date","Source Start Date"),("Source End Date","Source End Date"),("Occurrence Identity","Occurrence Identity"),("Source Time Evidence","Source Time Evidence"),("Current Category","Pipeline Category"),("Current Target","Pipeline Target"),("Current Disposition","Pipeline Disposition"))
    bad=[right for left,right in pairs if _norm(source.get(left))!=_norm(notion.get(right))]
    if bad: raise CurationIntegrityError(f"pipeline row identity differs for {source.get('Title')!r}: {bad}")


def _digest(payload): return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def _norm(value): return " ".join(str(value or "").strip().split())
