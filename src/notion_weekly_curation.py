"""Persistent, fail-closed Notion control surface for weekly event curation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable

import httpx

NOTION_API_VERSION = "2026-03-11"
PIPELINE_FIELDS = frozenset({"Curation Key", "Week", "Event Date", "Source", "Source Event ID", "Source URL", "Original Title", "Original Time", "Venue", "City", "Description", "Pipeline Category", "Pipeline Target", "Pipeline Disposition", "Pipeline Reason", "Category Confidence", "Category Reason", "Last Pipeline Sync", "Pipeline Run ID"})
CAPTAIN_FIELDS = frozenset({"Captain Include", "Captain Category", "Captain Target", "Captain Title Override", "Captain Time Override", "Captain Notes", "Curation Status"})
DERIVED_FIELDS = frozenset({"Event", "Final Category", "Final Target", "Final Inclusion"})
CATEGORIES = ("Music/Comedy", "Art/Theater", "Festivals/Fair", "Events/Hangouts", "Classes/Workshops", "Food & Drink", "Karaoke/Open Mic", "Sports", "Trivia/Game Night", "Fundraisers", "Lectures/Talks", "Markets", "Restaurants/Bars/Wineries", "Community Programs", "Weekly Events", "School District Event", "Tours", "Estate/Yard/Garage Sales", "Faith Based")
CAPTAIN_ALLOWED = {"Captain Include": {"", "INCLUDE", "EXCLUDE"}, "Captain Category": {"", *CATEGORIES}, "Captain Target": {"", "MAIN", "COMMUNITY"}, "Curation Status": {"", "NEEDS REVIEW", "REVIEWED"}}

class CurationIntegrityError(RuntimeError): pass

def curation_key(row: dict[str, Any], week: str) -> str:
    source = _norm(row.get("Source") or row.get("source"))
    event_id = _norm(row.get("Source Event ID") or row.get("source_event_id"))
    occurrence = _date(row.get("Event Date") or row.get("Date") or row.get("event_date"))
    if event_id:
        identity = f"v1|{week}|{source.casefold()}|id:{event_id}|{occurrence}"
    else:
        stable = "|".join((_norm(row.get("Original Title") or row.get("Title")).casefold(), _norm(row.get("Venue")).casefold(), _norm(row.get("Original Time") or _time(row))))
        identity = f"v1|{week}|{source.casefold()}|fallback:{stable}|{occurrence}"
    return "wc_" + hashlib.sha256(identity.encode()).hexdigest()[:32]

def schema() -> dict[str, Any]:
    select=lambda values: {"select":{"options":[{"name":v} for v in values]}}
    rich=lambda: {"rich_text":{}}
    return {"Event":{"title":{}}, "Curation Key":rich(), "Week":{"date":{}}, "Event Date":{"date":{}}, "Source":select([]), "Source Event ID":rich(), "Source URL":{"url":{}}, "Original Title":rich(), "Original Time":rich(), "Venue":rich(), "City":rich(), "Description":rich(), "Pipeline Category":select(CATEGORIES), "Pipeline Target":select(("MAIN","COMMUNITY")), "Pipeline Disposition":select(("AUTO_PUBLISH","REVIEW","REJECT")), "Pipeline Reason":rich(), "Category Confidence":{"number":{"format":"number"}}, "Category Reason":rich(), "Captain Include":select(("INCLUDE","EXCLUDE")), "Captain Category":select(CATEGORIES), "Captain Target":select(("MAIN","COMMUNITY")), "Captain Title Override":rich(), "Captain Time Override":rich(), "Captain Notes":rich(), "Curation Status":select(("NEEDS REVIEW","REVIEWED")), "Final Category":rich(), "Final Target":select(("MAIN","COMMUNITY")), "Final Inclusion":rich(), "Last Pipeline Sync":{"date":{}}, "Pipeline Run ID":rich()}

@dataclass
class NotionCurationClient:
    token: str
    data_source_id: str
    client: httpx.Client | None = None
    def __post_init__(self): self._client=self.client or httpx.Client(timeout=30)
    def close(self):
        if self.client is None: self._client.close()
    def query_week(self, week: str) -> list[dict[str, Any]]:
        out=[]; cursor=None
        while True:
            body={"page_size":100,"filter":{"property":"Week","date":{"equals":week}}}
            if cursor: body["start_cursor"]=cursor
            response=self._client.post(f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",headers=_headers(self.token),json=body); response.raise_for_status(); payload=response.json()
            out.extend(payload.get("results", [])); cursor=payload.get("next_cursor")
            if not payload.get("has_more") or not cursor: return out
    def create(self, properties):
        r=self._client.post("https://api.notion.com/v1/pages",headers=_headers(self.token),json={"parent":{"type":"data_source_id","data_source_id":self.data_source_id},"properties":properties}); r.raise_for_status(); return r.json()
    def update(self,page_id,properties):
        r=self._client.patch(f"https://api.notion.com/v1/pages/{page_id}",headers=_headers(self.token),json={"properties":properties}); r.raise_for_status(); return r.json()

def sync_week(client: NotionCurationClient, rows: Iterable[dict[str, Any]], *, week: str, run_id: str, migrate_captain: bool=False) -> dict[str, Any]:
    incoming=list(rows); existing=client.query_week(week); by_key={}; incoming_keys=set()
    for page in existing:
        key=_prop(page,"Curation Key")
        if key in by_key: raise CurationIntegrityError(f"duplicate Curation Key: {key}")
        by_key[key]=page
    created=updated=unchanged=preserved=0
    for row in incoming:
        key=curation_key(row,week); props=_serialize(row,week,key,run_id,include_captain=migrate_captain)
        if key in incoming_keys: raise CurationIntegrityError(f"duplicate incoming Curation Key: {key}")
        incoming_keys.add(key)
        page=by_key.get(key)
        if page is None: client.create(props); created+=1
        else:
            captain_before={name:_prop(page,name) for name in CAPTAIN_FIELDS}
            if _pipeline_matches(page, props): unchanged+=1
            else: client.update(page["id"],props); updated+=1
            preserved+=sum(v not in (None,"") for v in captain_before.values())
    read_back=read_week(client,week)
    read_keys={row["Curation Key"] for row in read_back}
    if read_keys != incoming_keys:
        missing=sorted(incoming_keys-read_keys); unexpected=sorted(read_keys-incoming_keys)
        raise CurationIntegrityError(f"incomplete sync: missing={missing} unexpected={unexpected}")
    return {"source_inventory_count":len(incoming),"created_rows":created,"updated_rows":updated,"unchanged_rows":unchanged,"captain_fields_preserved":preserved,"rows_before":len(existing),"rows_after":len(read_back)}

def read_week(client: NotionCurationClient, week: str) -> list[dict[str, Any]]:
    pages=client.query_week(week); rows=[]; seen=set()
    for page in pages:
        row={name:_prop(page,name) for name in PIPELINE_FIELDS|CAPTAIN_FIELDS|DERIVED_FIELDS}
        key=row["Curation Key"]
        if key in seen: raise CurationIntegrityError(f"duplicate Curation Key: {key}")
        seen.add(key)
        for field, allowed in CAPTAIN_ALLOWED.items():
            value=row.get(field) or ""
            if value not in allowed: raise CurationIntegrityError(f"malformed {field}: {value!r}")
        rows.append(row)
    return rows

def apply_captain_authority(row: dict[str,Any]) -> dict[str,Any]:
    include=_norm(row.get("Captain Include")); result=dict(row)
    result["Final Category"]=_norm(row.get("Captain Category")) or _norm(row.get("Pipeline Category"))
    result["Final Target"]=_norm(row.get("Captain Target")) or _norm(row.get("Pipeline Target"))
    result["Event"]=_norm(row.get("Captain Title Override")) or _norm(row.get("Original Title"))
    result["Final Time"]=_norm(row.get("Captain Time Override")) or _norm(row.get("Original Time"))
    result["Final Inclusion"]="INCLUDE" if include=="INCLUDE" else "EXCLUDE" if include=="EXCLUDE" else _norm(row.get("Pipeline Disposition"))
    return result

def _serialize(row,week,key,run_id,include_captain=False):
    now=datetime.now(timezone.utc).isoformat(); title=_norm(row.get("Original Title") or row.get("Title")); original_time=_norm(row.get("Original Time") or _time(row)); event_date=_date(row.get("Event Date") or row.get("Date"))
    values={"Event":title,"Curation Key":key,"Week":week,"Event Date":event_date,"Source":_norm(row.get("Source")),"Source Event ID":_norm(row.get("Source Event ID")),"Source URL":_norm(row.get("Source URL") or row.get("URL")),"Original Title":title,"Original Time":original_time,"Venue":_norm(row.get("Venue")),"City":_norm(row.get("City")),"Description":_norm(row.get("Description")),"Pipeline Category":_norm(row.get("Pipeline Category") or row.get("Current Category")),"Pipeline Target":_norm(row.get("Pipeline Target") or row.get("Current Target")),"Pipeline Disposition":_norm(row.get("Pipeline Disposition") or row.get("Current Disposition")),"Pipeline Reason":_norm(row.get("Pipeline Reason") or row.get("Editorial Reason") or row.get("Rejection Reason")),"Category Confidence":row.get("Category Confidence") or None,"Category Reason":_norm(row.get("Category Reason")),"Last Pipeline Sync":now,"Pipeline Run ID":run_id}
    if include_captain:
        for field in CAPTAIN_FIELDS: values[field]=_norm(row.get(field))
    final=apply_captain_authority({**values,**{f:_norm(row.get(f)) for f in CAPTAIN_FIELDS}})
    values.update({"Event":final["Event"],"Final Category":final["Final Category"],"Final Target":final["Final Target"],"Final Inclusion":final["Final Inclusion"]})
    return {name:_notion_value(name,value) for name,value in values.items() if name not in CAPTAIN_FIELDS or include_captain}

def _notion_value(name,value):
    if name in {"Event"}: return {"title":[{"text":{"content":str(value)[:2000]}}]}
    if name in {"Week","Event Date","Last Pipeline Sync"}: return {"date":{"start":str(value)} if value else None}
    if name in {"Source URL"}: return {"url":value or None}
    if name in {"Source","Pipeline Category","Pipeline Target","Pipeline Disposition","Captain Include","Captain Category","Captain Target","Curation Status","Final Target"}: return {"select":{"name":str(value)} if value else None}
    if name=="Category Confidence": return {"number":float(value) if value not in (None,"") else None}
    return {"rich_text":[{"text":{"content":str(value)[:2000]}}] if value not in (None,"") else []}

def _prop(page,name):
    prop=page.get("properties",{}).get(name,{})
    typ=prop.get("type")
    if typ in {"title","rich_text"}: return "".join(x.get("plain_text","") for x in prop.get(typ,[]))
    if typ=="select": return (prop.get("select") or {}).get("name","")
    if typ=="url": return prop.get("url") or ""
    if typ=="number": return prop.get("number")
    if typ=="date": return (prop.get("date") or {}).get("start","")
    return ""
def _pipeline_matches(page, properties):
    for name, value in properties.items():
        if name in {"Last Pipeline Sync", "Pipeline Run ID", *DERIVED_FIELDS}: continue
        if _norm(_prop(page,name)) != _norm(_serialized_value(value)): return False
    return True
def _serialized_value(prop):
    if "title" in prop: return "".join(x.get("text",{}).get("content","") for x in prop["title"])
    if "rich_text" in prop: return "".join(x.get("text",{}).get("content","") for x in prop["rich_text"])
    if "select" in prop: return (prop.get("select") or {}).get("name","")
    if "date" in prop: return (prop.get("date") or {}).get("start","")
    if "url" in prop: return prop.get("url") or ""
    if "number" in prop: return prop.get("number")
    return ""
def _norm(v): return re.sub(r"\s+"," ",str(v or "").strip())
def _date(v):
    text=_norm(v)
    for fmt in ("%Y-%m-%d","%m/%d/%Y"):
        try:return datetime.strptime(text,fmt).strftime("%Y-%m-%d")
        except ValueError:pass
    raise CurationIntegrityError(f"invalid occurrence date: {text!r}")
def _time(row):
    a=_norm(row.get("Start Time")); b=_norm(row.get("End Time")); return f"{a}-{b}" if a and b else a or b
def _headers(token): return {"Authorization":f"Bearer {token}","Notion-Version":NOTION_API_VERSION,"Content-Type":"application/json"}
