import json
import sys
from types import SimpleNamespace

import pytest

import tools.render_reddit_curated as command
from src.publisher_editorial import EditorialEvent


def editorial():
    return EditorialEvent(title="Captain Title",start_date="2026-08-11",end_date=None,display_start_time="10:00",display_end_time=None,display_time="7p",display_venue="Studio",display_city="Richland",display_organization=None,publication_url="https://example.com",publication_disposition="AUTO_PUBLISH",editorial_reason=None,publication_target="COMMUNITY",semantic_category="Sports",source="AllEvents",source_event_id="123",venue_id=None,venue_type=None,geographic_scope="LOCAL",region="MID_COLUMBIA",location_type=None,category="Sports",description=None,eventbrite_event_id=None,duplicate_sources=(),duplicate_count=1)


def run(monkeypatch,tmp_path,ready=True):
    inventory=tmp_path/"inventory.json"; inventory.write_text("{}",encoding="utf-8")
    audit=tmp_path/"audit.json"; audit.write_text(json.dumps({"inventory_count":1,"production_evidence":{"production_status":"HEALTHY","sources":[],"source_durations_ms":{},"warnings":[]}}),encoding="utf-8")
    calls=[]
    class Client:
        def __init__(self,*args): calls.append("notion_read_client")
        def close(self): calls.append("notion_close")
        def create(self,*args): raise AssertionError("Notion write forbidden")
        def update(self,*args): raise AssertionError("Notion write forbidden")
    monkeypatch.setenv("NOTION_TOKEN","token")
    monkeypatch.setattr(command,"NotionCurationClient",Client)
    monkeypatch.setattr(command,"load_curated_editorial",lambda *a,**k:[editorial()])
    monkeypatch.setattr(command,"write_reddit_artifact",lambda *a,**k:calls.append("render"))
    monkeypatch.setattr(command,"write_publisher_audit",lambda *a,**k:calls.append("audit"))
    monkeypatch.setattr(command,"write_production_mission_control",lambda **kwargs:(calls.append(("gate",kwargs)) or SimpleNamespace(ready_to_publish=ready,captain_summary="held"),{"archive_dashboard":tmp_path/"archive"/"dashboard.html"}))
    monkeypatch.setattr(sys,"argv",["render_reddit_curated","--week-start","2026-08-10","--curation-inventory",str(inventory),"--curation-sync-audit",str(audit)])
    return calls


def test_curated_render_invokes_production_gate_and_preserves_overrides(monkeypatch,tmp_path):
    calls=run(monkeypatch,tmp_path)
    assert command.main()==0
    gate=next(value for value in calls if isinstance(value,tuple) and value[0]=="gate")[1]
    assert gate["counts"]["community"]==1
    assert gate["counts"]["publication_blockers"]==0
    assert calls.count("render")==2
    assert not hasattr(command,"harvest_adapter")
    assert not hasattr(command,"publish")


def test_production_gate_failure_aborts_curated_readiness(monkeypatch,tmp_path):
    calls=run(monkeypatch,tmp_path,ready=False)
    with pytest.raises(RuntimeError,match="Mission Control held"):
        command.main()
    assert any(isinstance(value,tuple) and value[0]=="gate" for value in calls)


def test_success_stops_before_publication(monkeypatch,tmp_path):
    calls=run(monkeypatch,tmp_path,ready=True)
    assert command.main()==0
    assert "notion_read_client" in calls and "notion_close" in calls
