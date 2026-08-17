"""Persistent, fail-closed Notion control surface for weekly event curation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import time
from typing import Any, Iterable

import httpx

from src.notion_live import _fetch_venue
from src.occurrence_identity import canonical_occurrence_identity

NOTION_API_VERSION = "2026-03-11"
PIPELINE_FIELDS = frozenset({"Curation Key", "Week", "Event Date", "Source Start Date", "Source End Date", "Occurrence Identity", "Source Time Evidence", "Source", "Source Event ID", "Source URL", "Original Title", "Original Time", "Venue", "City", "Description", "Pipeline Category", "Pipeline Target", "Pipeline Disposition", "Pipeline Reason", "Category Confidence", "Category Reason", "Last Pipeline Sync", "Pipeline Run ID"})
CAPTAIN_FIELDS = frozenset({"Captain Include", "Captain Category", "Captain Target", "Captain Title Override", "Captain Time Override", "Captains Venue Override", "Captain Description Override", "Captain Notes", "Curation Status"})
DERIVED_FIELDS = frozenset({"Event", "Final Category", "Final Target", "Final Inclusion"})
CATEGORIES = ("Music/Comedy", "Art/Theater", "Festivals/Fair", "Events/Hangouts", "Classes/Workshops", "Food & Drink", "Karaoke/Open Mic", "Sports", "Trivia/Game Night", "Fundraisers", "Lectures/Talks", "Markets", "Restaurants/Bars/Wineries", "Community Programs", "Weekly Events", "School District Event", "Tours", "Estate/Yard/Garage Sales", "Faith Based")
CAPTAIN_ALLOWED = {"Captain Include": {"", "INCLUDE", "EXCLUDE"}, "Captain Category": {"", *CATEGORIES}, "Captain Target": {"", "MAIN", "COMMUNITY"}, "Curation Status": {"", "NEEDS REVIEW", "REVIEWED"}}
READ_BACK_ATTEMPTS = 3
READ_BACK_RETRY_DELAY_SECONDS = 1.0
WRITE_ATTEMPTS = 3
WRITE_RETRY_DELAY_SECONDS = 1.0

class CurationIntegrityError(RuntimeError): pass

def curation_key(row: dict[str, Any], week: str) -> str:
    occurrence = _date(
        row.get("Event Date")
        or row.get("Date")
        or row.get("event_date")
        or row.get("occurrence_date")
        or row.get("start_date")
    )
    identity = canonical_occurrence_identity(row, occurrence, week=week)
    return "wc_" + hashlib.sha256(identity.encode()).hexdigest()[:32]

def schema() -> dict[str, Any]:
    select=lambda values: {"select":{"options":[{"name":v} for v in values]}}
    rich=lambda: {"rich_text":{}}
    return {"Event":{"title":{}}, "Curation Key":rich(), "Week":{"date":{}}, "Event Date":{"date":{}}, "Source Start Date":{"date":{}}, "Source End Date":{"date":{}}, "Occurrence Identity":rich(), "Source Time Evidence":rich(), "Source":select([]), "Source Event ID":rich(), "Source URL":{"url":{}}, "Original Title":rich(), "Original Time":rich(), "Venue":rich(), "City":rich(), "Description":rich(), "Pipeline Category":select(CATEGORIES), "Pipeline Target":select(("MAIN","COMMUNITY")), "Pipeline Disposition":select(("AUTO_PUBLISH","REVIEW","REJECT")), "Pipeline Reason":rich(), "Category Confidence":{"number":{"format":"number"}}, "Category Reason":rich(), "Captain Include":select(("INCLUDE","EXCLUDE")), "Captain Category":select(CATEGORIES), "Captain Target":select(("MAIN","COMMUNITY")), "Captain Title Override":rich(), "Captain Time Override":rich(), "Captain Notes":rich(), "Curation Status":select(("NEEDS REVIEW","REVIEWED")), "Final Category":rich(), "Final Target":select(("MAIN","COMMUNITY")), "Final Inclusion":rich(), "Last Pipeline Sync":{"date":{}}, "Pipeline Run ID":rich()}

@dataclass
class NotionCurationClient:
    token: str
    data_source_id: str
    client: httpx.Client | None = None
    def __post_init__(self): self._client=self.client or httpx.Client(timeout=30)
    def close(self):
        if self.client is None: self._client.close()
    def resolve_venue_override(self,page_id: str) -> dict[str,str]:
        if not str(page_id or "").strip():
            raise CurationIntegrityError("Captain venue override is missing a relation page ID")
        venue=_fetch_venue(self._client,self.token,page_id)
        if not venue.get("Venue Name"):
            raise CurationIntegrityError(f"Captain venue override {page_id} lacks a canonical name")
        return venue
    def query_week(self, week: str) -> list[dict[str, Any]]:
        out=[]; cursor=None
        while True:
            body={"page_size":100,"filter":{"property":"Week","date":{"equals":week}}}
            if cursor: body["start_cursor"]=cursor
            response=self._client.post(f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",headers=_headers(self.token),json=body); response.raise_for_status(); payload=response.json()
            out.extend(payload.get("results", [])); cursor=payload.get("next_cursor")
            if not payload.get("has_more") or not cursor: return out
    def create(self, properties):
        try:
            r=self._client.post("https://api.notion.com/v1/pages",headers=_headers(self.token),json={"parent":{"type":"data_source_id","data_source_id":self.data_source_id},"properties":properties}); r.raise_for_status(); return r.json()
        except httpx.TransportError as error:
            return self._reconcile_unknown_create(properties,error)
    def update(self,page_id,properties,*,expected_before=None):
        error=None
        for attempt in range(WRITE_ATTEMPTS):
            try:
                r=self._client.patch(f"https://api.notion.com/v1/pages/{page_id}",headers=_headers(self.token),json={"properties":properties}); r.raise_for_status(); return r.json()
            except httpx.TransportError as caught:
                error=caught
                current=self._read_page_for_reconciliation(page_id)
                state=_update_reconciliation_state(current,properties,expected_before)
                if state=="applied": return current
                if state!="not_applied":
                    raise CurationIntegrityError(f"ambiguous Notion update outcome for page {page_id}") from caught
                if attempt+1<WRITE_ATTEMPTS: time.sleep(WRITE_RETRY_DELAY_SECONDS)
        raise CurationIntegrityError(f"Notion update retry budget exhausted for page {page_id}") from error
    def _read_page_for_reconciliation(self,page_id):
        error=None
        for attempt in range(WRITE_ATTEMPTS):
            try:
                r=self._client.get(f"https://api.notion.com/v1/pages/{page_id}",headers=_headers(self.token)); r.raise_for_status(); return r.json()
            except httpx.TransportError as caught:
                error=caught
                if attempt+1<WRITE_ATTEMPTS: time.sleep(WRITE_RETRY_DELAY_SECONDS)
        raise CurationIntegrityError(f"unable to reconcile unknown Notion write for page {page_id}") from error
    def _query_key_for_reconciliation(self,key):
        r=self._client.post(f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",headers=_headers(self.token),json={"page_size":100,"filter":{"property":"Curation Key","rich_text":{"equals":key}}}); r.raise_for_status(); return r.json().get("results",[])
    def _reconcile_unknown_create(self,properties,error):
        key=_serialized_value(properties.get("Curation Key",{}))
        if not key: raise CurationIntegrityError("cannot reconcile unknown Notion create without Curation Key") from error
        last_error=error
        for attempt in range(WRITE_ATTEMPTS):
            try: pages=self._query_key_for_reconciliation(key)
            except httpx.TransportError as caught:
                pages=[]; last_error=caught
            if len(pages)>1: raise CurationIntegrityError(f"ambiguous Notion create outcome: duplicate Curation Key {key}") from error
            if len(pages)==1:
                if _payload_matches(pages[0],properties): return pages[0]
                raise CurationIntegrityError(f"ambiguous Notion create outcome: identity or payload differs for {key}") from error
            if attempt+1<WRITE_ATTEMPTS: time.sleep(WRITE_RETRY_DELAY_SECONDS)
        raise CurationIntegrityError(f"unknown Notion create outcome for {key}; no safe create retry") from last_error

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
            if _pipeline_matches(page, props):
                client.update(page["id"], {name:props[name] for name in ("Last Pipeline Sync","Pipeline Run ID")},expected_before=page)
                unchanged+=1
            else: client.update(page["id"],props,expected_before=page); updated+=1
            preserved+=sum(v not in (None,"") for v in captain_before.values())
    read_back=[]; current_rows=[]; current_keys=set(); retained=[]
    expected_props={curation_key(row,week):_serialize(row,week,curation_key(row,week),run_id,include_captain=migrate_captain) for row in incoming}
    attempts_used=0
    for attempt in range(READ_BACK_ATTEMPTS):
        attempts_used=attempt+1
        read_back=read_week(client,week)
        current_rows=[row for row in read_back if _norm(row.get("Pipeline Run ID"))==run_id]
        current_keys={row["Curation Key"] for row in current_rows}
        unexpected=sorted(current_keys-incoming_keys)
        if unexpected:
            raise CurationIntegrityError(f"unexpected current-run Curation Keys: {unexpected}")
        retained=_classify_retained_rows(
            [row for row in read_back if row["Curation Key"] not in incoming_keys], incoming
        )
        blockers=[item for item in retained if item["classification"] in {"CAPTAIN-BEARING RETAINED ROW","AMBIGUOUS IDENTITY"}]
        if blockers:
            raise CurationIntegrityError(f"retained same-week rows require review: {[item['curation_key'] for item in blockers]}")
        missing=sorted(incoming_keys-current_keys)
        if not missing: break
        if attempt + 1 < READ_BACK_ATTEMPTS:
            time.sleep(READ_BACK_RETRY_DELAY_SECONDS)
    missing=sorted(incoming_keys-current_keys)
    if missing:
        raise CurationIntegrityError(f"incomplete current-run sync after {READ_BACK_ATTEMPTS} read-back attempts: missing={missing} unexpected=[]")
    current_by_key={row["Curation Key"]:row for row in current_rows}
    malformed=[key for key,props in expected_props.items() if not _pipeline_values_match(current_by_key[key],props)]
    if malformed:
        raise CurationIntegrityError(f"malformed current-run pipeline rows: {malformed}")
    retained_counts={name:sum(item["classification"]==name for item in retained) for name in ("RETAINED / SOURCE ABSENT","RETAINED / SUPERSEDED IDENTITY","CAPTAIN-BEARING RETAINED ROW","AMBIGUOUS IDENTITY")}
    return {
        "source_inventory_count":len(incoming),"expected_current_inventory_count":len(incoming),
        "created_rows":created,"updated_rows":updated,"unchanged_rows":unchanged,
        "captain_fields_preserved":preserved,"rows_before":len(existing),"rows_after":len(read_back),
        "live_current_run_row_count":len(current_rows),"current_missing_keys":[],"current_unexpected_keys":[],
        "current_duplicate_keys":[],"current_malformed_keys":[],"read_back_attempts_used":attempts_used,
        "retained_same_week_row_count":len(retained),
        "retained_source_absent_count":retained_counts["RETAINED / SOURCE ABSENT"],
        "retained_superseded_identity_count":retained_counts["RETAINED / SUPERSEDED IDENTITY"],
        "retained_captain_bearing_count":retained_counts["CAPTAIN-BEARING RETAINED ROW"],
        "retained_ambiguous_count":retained_counts["AMBIGUOUS IDENTITY"],
        "retained_rows":retained,
    }

def read_week(client: NotionCurationClient, week: str) -> list[dict[str, Any]]:
    pages=client.query_week(week); rows=[]; seen=set()
    for page in pages:
        row={name:_prop(page,name) for name in PIPELINE_FIELDS|CAPTAIN_FIELDS|DERIVED_FIELDS}
        row["Page ID"]=page.get("id","")
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
    now=datetime.now(timezone.utc).isoformat(timespec="seconds"); title=_norm(row.get("Original Title") or row.get("Title")); original_time=_norm(row.get("Original Time") or _time(row)); event_date=_date(row.get("Event Date") or row.get("Date"))
    values={"Event":title,"Curation Key":key,"Week":week,"Event Date":event_date,"Source Start Date":_norm(row.get("Source Start Date")) or event_date,"Source End Date":_norm(row.get("Source End Date")) or event_date,"Occurrence Identity":_norm(row.get("Occurrence Identity")),"Source Time Evidence":_norm(row.get("Source Time Evidence")),"Source":_norm(row.get("Source")),"Source Event ID":_norm(row.get("Source Event ID")),"Source URL":_norm(row.get("Source URL") or row.get("URL")),"Original Title":title,"Original Time":original_time,"Venue":_norm(row.get("Venue")),"City":_norm(row.get("City")),"Description":_norm(row.get("Description")),"Pipeline Category":_norm(row.get("Pipeline Category") or row.get("Current Category")),"Pipeline Target":_norm(row.get("Pipeline Target") or row.get("Current Target")),"Pipeline Disposition":_norm(row.get("Pipeline Disposition") or row.get("Current Disposition")),"Pipeline Reason":_norm(row.get("Pipeline Reason") or row.get("Editorial Reason") or row.get("Rejection Reason")),"Category Confidence":row.get("Category Confidence") or None,"Category Reason":_norm(row.get("Category Reason")),"Last Pipeline Sync":now,"Pipeline Run ID":run_id}
    if include_captain:
        for field in CAPTAIN_FIELDS: values[field]=_norm(row.get(field))
    final=apply_captain_authority({**values,**{f:_norm(row.get(f)) for f in CAPTAIN_FIELDS}})
    values.update({"Event":final["Event"],"Final Category":final["Final Category"],"Final Target":final["Final Target"],"Final Inclusion":final["Final Inclusion"]})
    return {name:_notion_value(name,value) for name,value in values.items() if name not in CAPTAIN_FIELDS or include_captain}

def _notion_value(name,value):
    if name in {"Event"}: return {"title":[{"text":{"content":str(value)[:2000]}}]}
    if name in {"Week","Event Date","Source Start Date","Source End Date","Last Pipeline Sync"}: return {"date":{"start":str(value)} if value else None}
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
    if typ=="relation": return ",".join(item.get("id","") for item in prop.get("relation",[]) if item.get("id"))
    return ""
def _pipeline_matches(page, properties):
    for name, value in properties.items():
        if name in {"Last Pipeline Sync", "Pipeline Run ID", *DERIVED_FIELDS}: continue
        if not _property_values_equal(name,_prop(page,name),_serialized_value(value)): return False
    return True
def _pipeline_values_match(row, properties):
    for name,value in properties.items():
        if name in {"Last Pipeline Sync", "Pipeline Run ID", *DERIVED_FIELDS}: continue
        if not _property_values_equal(name,row.get(name),_serialized_value(value)): return False
    return True
def _payload_matches(page,properties):
    return all(_property_values_equal(name,_prop(page,name),_serialized_value(value)) for name,value in properties.items())
def _update_reconciliation_state(page,properties,before):
    if before is not None and _norm(_prop(page,"Curation Key"))!=_norm(_prop(before,"Curation Key")):
        return "ambiguous"
    intended={name:_serialized_value(value) for name,value in properties.items()}
    if all(_property_values_equal(name,_prop(page,name),value) for name,value in intended.items()): return "applied"
    if before is not None:
        if all(_property_values_equal(name,_prop(page,name),_prop(before,name)) for name in properties): return "not_applied"
    return "ambiguous"

def _property_values_equal(name,value,expected):
    if name=="Pipeline Run ID":
        return str(value or "")==str(expected or "")
    if name in {"Week","Event Date","Source Start Date","Source End Date"}:
        return _canonical_date_value(value)==_canonical_date_value(expected)
    if name=="Category Confidence":
        try:
            return Decimal(str(value))==Decimal(str(expected))
        except InvalidOperation:
            return value in (None,"") and expected in (None,"")
    if name=="Source Time Evidence":
        try:
            return json.loads(str(value))==json.loads(str(expected))
        except (TypeError,ValueError,json.JSONDecodeError):
            return _canonical_notion_text(value)==_canonical_notion_text(expected)
    return _canonical_notion_text(value)==_canonical_notion_text(expected)

def _canonical_date_value(value):
    text=_norm(value)
    if not text: return ""
    try: return datetime.fromisoformat(text.replace("Z","+00:00")).date().isoformat()
    except ValueError: return text

def _canonical_notion_text(value):
    text="" if value is None else str(value)
    text=text.replace("\u200b","")
    return _norm(text)
def _classify_retained_rows(rows, incoming):
    output=[]
    for row in rows:
        captain_fields=[name for name in CAPTAIN_FIELDS if _norm(row.get(name))]
        classification="CAPTAIN-BEARING RETAINED ROW" if captain_fields else _retained_identity_class(row,incoming)
        output.append({
            "curation_key":row.get("Curation Key") or "","page_id":row.get("Page ID") or "",
            "title":row.get("Original Title") or row.get("Event") or "","event_date":row.get("Event Date") or "",
            "source":row.get("Source") or "","source_event_id":row.get("Source Event ID") or "",
            "prior_pipeline_run_id":row.get("Pipeline Run ID") or "","classification":classification,
            "captain_bearing":bool(captain_fields),"captain_fields":sorted(captain_fields),
        })
    return output
def _retained_identity_class(row,incoming):
    source=_norm(row.get("Source")).casefold(); event_date=_norm(row.get("Event Date"))
    title=_norm(row.get("Original Title") or row.get("Event")).casefold(); venue=_norm(row.get("Venue")).casefold()
    city=_norm(row.get("City")).casefold(); event_id=_norm(row.get("Source Event ID"))
    occurrence_identity=_norm(row.get("Occurrence Identity"))
    candidates=[]
    for item in incoming:
        item_source=_norm(item.get("Source") or item.get("source")).casefold()
        item_date=_norm(item.get("Event Date") or item.get("Date") or item.get("start_date"))
        if item_source==source and item_date==event_date: candidates.append(item)
    for item in candidates:
        item_title=_norm(item.get("Original Title") or item.get("Title") or item.get("title")).casefold()
        item_venue=_norm(item.get("Venue") or item.get("venue")).casefold()
        item_city=_norm(item.get("City") or item.get("city")).casefold()
        item_id=_norm(item.get("Source Event ID") or item.get("source_event_id"))
        item_occurrence_identity=_norm(item.get("Occurrence Identity") or item.get("occurrence_identity"))
        title_match=bool(title and item_title and title==item_title)
        venue_match=bool(venue and item_venue and venue==item_venue)
        city_match=bool(city and item_city and city==item_city)
        ids_match=bool(event_id and item_id and event_id==item_id)
        ids_conflict=bool(event_id and item_id and event_id!=item_id)
        occurrence_match=bool(occurrence_identity and item_occurrence_identity and occurrence_identity==item_occurrence_identity)
        geography_compatible=not (city and item_city) or city_match
        if ids_conflict and title_match and venue_match and geography_compatible:
            return "RETAINED / SUPERSEDED IDENTITY"
        if occurrence_match or ids_match or (title_match and (venue_match or city_match)):
            return "AMBIGUOUS IDENTITY"
    return "RETAINED / SOURCE ABSENT"
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
