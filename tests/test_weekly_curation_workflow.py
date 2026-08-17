import json

import pytest

from src.notion_weekly_curation import CurationIntegrityError, curation_key
from src.publisher_editorial import EditorialEvent
import src.weekly_curation_workflow as workflow


def event():
    return EditorialEvent(
        title="Class",start_date="2026-08-11",end_date=None,display_start_time="10:00",display_end_time="11:00",display_time="10-11a",
        display_venue="Studio",display_city="Richland",display_organization=None,publication_url="https://example.com/event",
        publication_disposition="AUTO_PUBLISH",editorial_reason=None,publication_target="MAIN",semantic_category="Classes/Workshops",
        source="AllEvents",source_event_id="123",venue_id=None,venue_type=None,geographic_scope="LOCAL",region="MID_COLUMBIA",
        location_type=None,category="Classes/Workshops",description=None,eventbrite_event_id=None,duplicate_sources=(),duplicate_count=1,
        canonical_title="Class",
    )


def boundary(tmp_path, *, retained=None):
    row=workflow.inventory_rows([event()])[0]
    payload={"week":"2026-08-10","rows":[row]}
    inventory=tmp_path/"inventory.json"; audit=tmp_path/"audit.json"
    inventory.write_text(json.dumps(payload),encoding="utf-8")
    audit.write_text(json.dumps({"week":"2026-08-10","run_id":"run","inventory_count":1,"inventory_sha256":workflow._digest(payload),"sync":{"retained_rows":retained or []}}),encoding="utf-8")
    return row,inventory,audit


def notion_row(row, **captain):
    result={"Curation Key":curation_key(row,"2026-08-10"),"Original Title":row["Title"],"Event Date":row["Date"],"Source Start Date":row["Source Start Date"],"Source End Date":row["Source End Date"],"Occurrence Identity":row["Occurrence Identity"],"Source Time Evidence":row["Source Time Evidence"],"Source":row["Source"],"Source Event ID":row["Source Event ID"],"Source URL":row["URL"],"Venue":row["Venue"],"City":row["City"],"Pipeline Category":row["Current Category"],"Pipeline Target":row["Current Target"],"Pipeline Disposition":row["Current Disposition"],"Pipeline Run ID":"run","Original Time":"10:00-11:00"}
    result.update(captain); return result


def test_inventory_preserves_source_range_and_occurrence_identity():
    ranged = event()
    ranged = EditorialEvent(**{
        **ranged.to_dict(),
        "source_start_date": "2026-08-10",
        "source_end_date": "2026-08-13",
        "occurrence_identity": "v1|allevents|id:123|2026-08-11",
        "source_time_evidence": {"start_time": "10:00", "end_time": "11:00"},
    })
    row = workflow.inventory_rows([ranged])[0]
    assert row["Date"] == "2026-08-11"
    assert row["Source Start Date"] == "2026-08-10"
    assert row["Source End Date"] == "2026-08-13"
    assert row["Occurrence Identity"].endswith("|2026-08-11")
    assert json.loads(row["Source Time Evidence"])["start_time"] == "10:00"


def test_blank_captain_values_preserve_pipeline_defaults(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path)
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row)])
    rendered=workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)[0]
    assert (rendered.title,rendered.semantic_category,rendered.publication_target,rendered.publication_disposition)==("Class","Classes/Workshops","MAIN","AUTO_PUBLISH")


def test_explicit_captain_values_override_pipeline(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path)
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row,**{"Captain Include":"INCLUDE","Captain Category":"Sports","Captain Target":"COMMUNITY","Captain Title Override":"Captain Class","Captain Time Override":"7-8p"})])
    rendered=workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)[0]
    assert (rendered.title,rendered.display_time,rendered.semantic_category,rendered.publication_target)==("Captain Class","7-8p","Sports","COMMUNITY")

def test_captain_category_derives_target_when_target_override_is_blank(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path)
    row["Current Target"]="REVIEW"; row["Current Category"]=""
    payload={"week":"2026-08-10","rows":[row]}; inventory.write_text(json.dumps(payload),encoding="utf-8")
    audit.write_text(json.dumps({"week":"2026-08-10","run_id":"run","inventory_count":1,"inventory_sha256":workflow._digest(payload),"sync":{"retained_rows":[]}}),encoding="utf-8")
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row,**{"Captain Include":"INCLUDE","Captain Category":"Community Programs"})])
    rendered=workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)[0]
    assert rendered.publication_target=="COMMUNITY"

def test_audited_retained_rows_are_preserved_outside_frozen_cohort(monkeypatch,tmp_path):
    retained=[{"curation_key":"retained","title":"Old","event_date":"2026-08-09","source":"AllEvents","source_event_id":"old-1","prior_pipeline_run_id":"old"}]; row,inventory,audit=boundary(tmp_path,retained=retained)
    stale={"Curation Key":"retained","Original Title":"Old","Event Date":"2026-08-09","Source":"AllEvents","Source Event ID":"old-1","Pipeline Run ID":"old"}
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row),stale])
    assert len(workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit))==1

def test_unexpected_or_missing_audited_retained_row_aborts(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path,retained=[{"curation_key":"retained"}])
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row)])
    with pytest.raises(CurationIntegrityError,match="missing_retained"):
        workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)

def test_changed_retained_pipeline_identity_aborts(monkeypatch,tmp_path):
    retained=[{"curation_key":"retained","title":"Old","event_date":"2026-08-09","source":"AllEvents","source_event_id":"old-1","prior_pipeline_run_id":"old"}]; row,inventory,audit=boundary(tmp_path,retained=retained)
    stale={"Curation Key":"retained","Original Title":"Changed","Event Date":"2026-08-09","Source":"AllEvents","Source Event ID":"old-1","Pipeline Run ID":"old"}
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row),stale])
    with pytest.raises(CurationIntegrityError,match="retained row differs"):
        workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)

def test_retained_captain_state_remains_outside_frozen_projection(monkeypatch,tmp_path):
    retained=[{"curation_key":"retained","title":"Old","event_date":"2026-08-09","source":"AllEvents","source_event_id":"old-1","prior_pipeline_run_id":"old"}]; row,inventory,audit=boundary(tmp_path,retained=retained)
    stale={"Curation Key":"retained","Original Title":"Old","Event Date":"2026-08-09","Source":"AllEvents","Source Event ID":"old-1","Pipeline Run ID":"old","Captain Include":"EXCLUDE"}
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row),stale])
    assert len(workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit))==1

def test_captain_venue_and_description_overrides_are_applied(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path)
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row,**{"Captains Venue Override":"venue-page","Captain Description Override":"Captain description"})])
    client=type("Client",(),{"resolve_venue_override":lambda self,page_id:{"Venue Reddit Combo":"[Canonical Hall](https://hall.example/), Pasco","Venue Name":"Ignored","Venue URL":"https://ignored.example/","City":"Ignored"}})()
    rendered=workflow.load_curated_editorial(client,week="2026-08-10",inventory_path=inventory,audit_path=audit)[0]
    assert (rendered.display_venue,rendered.publication_url,rendered.display_city,rendered.description)==("Canonical Hall","https://hall.example/","Pasco","Captain description")

def test_invalid_captain_venue_override_fails_closed(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path)
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row,**{"Captains Venue Override":"venue-page"})])
    client=type("Client",(),{"resolve_venue_override":lambda self,page_id:{"Venue Name":"","Venue URL":"https://hall.example/","City":"Pasco"}})()
    with pytest.raises(CurationIntegrityError,match="lacks canonical presentation"):
        workflow.load_curated_editorial(client,week="2026-08-10",inventory_path=inventory,audit_path=audit)

def test_captain_venue_without_website_preserves_existing_publication_url(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path)
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row,**{"Captains Venue Override":"venue-page"})])
    client=type("Client",(),{"resolve_venue_override":lambda self,page_id:{"Venue Name":"Downtown","Venue URL":"","City":"Benton City"}})()
    rendered=workflow.load_curated_editorial(client,week="2026-08-10",inventory_path=inventory,audit_path=audit)[0]
    assert (rendered.display_venue,rendered.display_city,rendered.publication_url)==("Downtown","Richland","https://example.com/event")

def test_pipeline_original_title_drift_still_fails(monkeypatch,tmp_path):
    row,inventory,audit=boundary(tmp_path)
    monkeypatch.setattr(workflow,"read_week",lambda client,week:[notion_row(row,**{"Original Title":"Clas"})])
    with pytest.raises(CurationIntegrityError,match="Original Title"):
        workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)


def test_missing_row_aborts(monkeypatch,tmp_path):
    _,inventory,audit=boundary(tmp_path); monkeypatch.setattr(workflow,"read_week",lambda client,week:[])
    with pytest.raises(CurationIntegrityError,match="does not reconcile"):
        workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)


def test_missing_audit_aborts(tmp_path):
    with pytest.raises(CurationIntegrityError,match="boundary is missing"):
        workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=tmp_path/"missing-inventory",audit_path=tmp_path/"missing-audit")

def test_prepare_audit_records_retained_same_week_evidence(monkeypatch,tmp_path):
    retained=[
        {"curation_key":"stale-1","page_id":"page-1","title":"Trivia Thursdays","event_date":"2026-08-20","source":"AllEvents","source_event_id":"old-1","prior_pipeline_run_id":"old","classification":"RETAINED / SOURCE ABSENT","captain_bearing":False,"captain_fields":[]},
        {"curation_key":"stale-2","page_id":"page-2","title":"AquaSox","event_date":"2026-08-23","source":"AllEvents","source_event_id":"old-2","prior_pipeline_run_id":"old","classification":"RETAINED / SUPERSEDED IDENTITY","captain_bearing":False,"captain_fields":[]},
    ]
    sync={"source_inventory_count":1,"expected_current_inventory_count":1,"live_current_run_row_count":1,"current_missing_keys":[],"current_unexpected_keys":[],"current_duplicate_keys":[],"retained_same_week_row_count":2,"retained_source_absent_count":1,"retained_superseded_identity_count":1,"retained_captain_bearing_count":0,"retained_ambiguous_count":0,"retained_rows":retained}
    monkeypatch.setattr(workflow,"sync_week",lambda *args,**kwargs:sync)
    inventory=tmp_path/"inventory.json"; audit_path=tmp_path/"audit.json"

    audit=workflow.prepare_curation(type("Client",(),{"data_source_id":"source"})(),[event()],week="2026-08-10",run_id="current",inventory_path=inventory,audit_path=audit_path)

    assert audit["sync"]["retained_rows"]==retained
    assert json.loads(audit_path.read_text(encoding="utf-8"))["sync"]["retained_superseded_identity_count"]==1
    assert len(json.loads(inventory.read_text(encoding="utf-8"))["rows"])==1
