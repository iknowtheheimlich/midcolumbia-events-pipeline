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


def boundary(tmp_path):
    row=workflow.inventory_rows([event()])[0]
    payload={"week":"2026-08-10","rows":[row]}
    inventory=tmp_path/"inventory.json"; audit=tmp_path/"audit.json"
    inventory.write_text(json.dumps(payload),encoding="utf-8")
    audit.write_text(json.dumps({"week":"2026-08-10","inventory_count":1,"inventory_sha256":workflow._digest(payload)}),encoding="utf-8")
    return row,inventory,audit


def notion_row(row, **captain):
    result={"Curation Key":curation_key(row,"2026-08-10"),"Original Title":row["Title"],"Event Date":row["Date"],"Source Start Date":row["Source Start Date"],"Source End Date":row["Source End Date"],"Occurrence Identity":row["Occurrence Identity"],"Source Time Evidence":row["Source Time Evidence"],"Source":row["Source"],"Source Event ID":row["Source Event ID"],"Source URL":row["URL"],"Venue":row["Venue"],"City":row["City"],"Pipeline Category":row["Current Category"],"Pipeline Target":row["Current Target"],"Pipeline Disposition":row["Current Disposition"],"Original Time":"10:00-11:00"}
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


def test_missing_row_aborts(monkeypatch,tmp_path):
    _,inventory,audit=boundary(tmp_path); monkeypatch.setattr(workflow,"read_week",lambda client,week:[])
    with pytest.raises(CurationIntegrityError,match="does not reconcile"):
        workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=inventory,audit_path=audit)


def test_missing_audit_aborts(tmp_path):
    with pytest.raises(CurationIntegrityError,match="boundary is missing"):
        workflow.load_curated_editorial(object(),week="2026-08-10",inventory_path=tmp_path/"missing-inventory",audit_path=tmp_path/"missing-audit")
