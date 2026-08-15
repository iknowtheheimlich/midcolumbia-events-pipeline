import copy
import pytest

from src.notion_weekly_curation import CAPTAIN_FIELDS, CurationIntegrityError, apply_captain_authority, curation_key, read_week, sync_week

def row(**changes):
    base={"Date":"2026-08-11","Source":"AllEvents","Source Event ID":"123","Title":"Class","Start Time":"10a","End Time":"11a","Venue":"Studio","City":"Richland","Current Category":"Classes/Workshops","Current Target":"MAIN","Current Disposition":"AUTO_PUBLISH"}
    base.update(changes); return base

def page(key, **values):
    props={"Curation Key":{"type":"rich_text","rich_text":[{"plain_text":key}]}}
    for name,value in values.items():
        if name=="Captains Venue Override":
            props[name]={"type":"relation","relation":[{"id":value}] if value else []}
        else:
            props[name]={"type":"select","select":{"name":value} if value else None}
    return {"id":"page-1","properties":props}

class FakeClient:
    def __init__(self,pages=()): self.pages=list(pages); self.created=[]; self.updated=[]
    def query_week(self,week): return copy.deepcopy(self.pages)
    def create(self,properties): self.created.append(properties); self.pages.append({"id":f"created-{len(self.created)}","properties":_as_page_properties(properties)})
    def update(self,page_id,properties):
        self.updated.append((page_id,properties))
        target=next(item for item in self.pages if item["id"]==page_id)
        target["properties"].update(_as_page_properties(properties))

class EventuallyConsistentClient(FakeClient):
    def __init__(self):
        super().__init__(); self.queries=0
    def query_week(self,week):
        self.queries+=1
        if self.queries==2:
            return []
        return super().query_week(week)

def _as_page_properties(properties):
    result={}
    for name,value in properties.items():
        if "title" in value: result[name]={"type":"title","title":[{"plain_text":x["text"]["content"]} for x in value["title"]]}
        elif "rich_text" in value: result[name]={"type":"rich_text","rich_text":[{"plain_text":x["text"]["content"]} for x in value["rich_text"]]}
        elif "select" in value: result[name]={"type":"select","select":value["select"]}
        elif "date" in value: result[name]={"type":"date","date":value["date"]}
        elif "url" in value: result[name]={"type":"url","url":value["url"]}
        elif "number" in value: result[name]={"type":"number","number":value["number"]}
    return result

def test_deterministic_key_and_distinct_occurrences():
    assert curation_key(row(),"2026-08-10")==curation_key(row(),"2026-08-10")
    assert curation_key(row(),"2026-08-10")!=curation_key(row(Date="2026-08-12"),"2026-08-10")

def test_fallback_key_uses_stable_evidence_not_mutable_decisions():
    a=row(**{"Source Event ID":"","Current Category":"Sports","Captain Include":"INCLUDE"})
    b=row(**{"Source Event ID":"","Current Category":"Music/Comedy","Captain Include":"EXCLUDE"})
    assert curation_key(a,"2026-08-10")==curation_key(b,"2026-08-10")

def test_initial_creation_and_idempotent_update_preserve_captain_fields():
    item=row(**{"Captain Include":"INCLUDE"}); first=FakeClient()
    result=sync_week(first,[item],week="2026-08-10",run_id="run",migrate_captain=True)
    assert result["created_rows"]==1
    key=curation_key(item,"2026-08-10"); second=FakeClient([page(key,**{"Captain Include":"INCLUDE","Captain Target":"COMMUNITY"})])
    result=sync_week(second,[row(Title="Updated")],week="2026-08-10",run_id="run2")
    assert result["updated_rows"]==1
    properties=second.updated[0][1]
    assert CAPTAIN_FIELDS.isdisjoint(properties)
    assert properties["Original Title"]["rich_text"][0]["text"]["content"]=="Updated"

def test_occurrence_evidence_uses_exact_notion_schema_types():
    item=row(**{
        "Source Start Date":"2026-08-10",
        "Source End Date":"2026-08-13",
        "Occurrence Identity":"allevents|123|2026-08-11",
        "Source Time Evidence":'{"start_time":"10:00","end_time":"11:00"}',
    })
    fake=FakeClient()

    sync_week(fake,[item],week="2026-08-10",run_id="run")

    properties=fake.created[0]
    assert properties["Source Start Date"]=={"date":{"start":"2026-08-10"}}
    assert properties["Source End Date"]=={"date":{"start":"2026-08-13"}}
    assert properties["Occurrence Identity"]=={"rich_text":[{"text":{"content":"allevents|123|2026-08-11"}}]}
    assert properties["Source Time Evidence"]=={"rich_text":[{"text":{"content":'{"start_time":"10:00","end_time":"11:00"}'}}]}
    assert CAPTAIN_FIELDS.isdisjoint(properties)

    single=FakeClient()
    sync_week(single,[row()],week="2026-08-10",run_id="single")
    assert single.created[0]["Source Start Date"]=={"date":{"start":"2026-08-11"}}
    assert single.created[0]["Source End Date"]=={"date":{"start":"2026-08-11"}}

def test_blank_captain_fields_migrate_as_blank():
    fake=FakeClient(); sync_week(fake,[row()],week="2026-08-10",run_id="run",migrate_captain=True)
    assert fake.created[0]["Captain Include"]=={"select":None}

@pytest.mark.parametrize(("field","value","expected"),[("Captain Include","INCLUDE",("Final Inclusion","INCLUDE")),("Captain Include","EXCLUDE",("Final Inclusion","EXCLUDE")),("Captain Category","Sports",("Final Category","Sports")),("Captain Target","COMMUNITY",("Final Target","COMMUNITY")),("Captain Title Override","New title",("Event","New title")),("Captain Time Override","7-9p",("Final Time","7-9p"))])
def test_captain_authority(field,value,expected):
    data={"Pipeline Category":"Classes/Workshops","Pipeline Target":"MAIN","Pipeline Disposition":"REVIEW","Original Title":"Old","Original Time":"6p",field:value}
    assert apply_captain_authority(data)[expected[0]]==expected[1]

def test_notes_are_non_executable():
    result=apply_captain_authority({"Pipeline Disposition":"REVIEW","Captain Notes":"INCLUDE this"})
    assert result["Final Inclusion"]=="REVIEW"

def test_duplicate_key_fails():
    duplicate=page("same")
    with pytest.raises(CurationIntegrityError,match="duplicate"):
        sync_week(FakeClient([duplicate,duplicate]),[row()],week="2026-08-10",run_id="run")

def test_malformed_captain_value_fails():
    with pytest.raises(CurationIntegrityError,match="malformed"):
        read_week(FakeClient([page("key",**{"Captain Include":"MAYBE"})]),"2026-08-10")

def test_query_pagination():
    import httpx
    from src.notion_weekly_curation import NotionCurationClient
    calls=[]
    def handler(request):
        body=request.content.decode(); calls.append(body)
        return httpx.Response(200,json={"results":[page(str(len(calls)))],"has_more":len(calls)==1,"next_cursor":"next" if len(calls)==1 else None})
    transport=httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as raw:
        client=NotionCurationClient("token","source",raw)
        assert len(client.query_week("2026-08-10"))==2
    assert "start_cursor" in calls[1]

def test_sync_retries_incomplete_eventually_consistent_read_back(monkeypatch):
    import src.notion_weekly_curation as curation
    monkeypatch.setattr(curation.time,"sleep",lambda _: None)
    fake=EventuallyConsistentClient()

    result=sync_week(fake,[row()],week="2026-08-10",run_id="run")

    assert result["created_rows"]==1
    assert result["rows_after"]==1
    assert fake.queries==3
    assert len(fake.created)==1

def test_clean_source_absent_retained_row_is_audited_without_retry(monkeypatch):
    import src.notion_weekly_curation as curation
    sleeps=[]; monkeypatch.setattr(curation.time,"sleep",lambda value:sleeps.append(value))
    stale=page("stale",**{"Pipeline Run ID":"old","Original Title":"Trivia Thursdays","Event Date":"2026-08-20","Source":"AllEvents","Source Event ID":"old-trivia","Venue":"Summers Hub"})
    fake=FakeClient([stale])

    result=sync_week(fake,[row()],week="2026-08-10",run_id="current")

    assert result["live_current_run_row_count"]==1
    assert result["retained_source_absent_count"]==1
    assert result["retained_rows"][0]["classification"]=="RETAINED / SOURCE ABSENT"
    assert result["retained_rows"][0]["page_id"]=="page-1"
    assert result["retained_rows"][0]["prior_pipeline_run_id"]=="old"
    assert result["read_back_attempts_used"]==1
    assert sleeps==[]
    assert len(fake.created)==1
    assert not hasattr(fake,"deleted")

def test_superseded_source_identity_is_retained_without_migration():
    current=row(Date="2026-08-23",Title="Everett AquaSox at Tri-City Dust Devils",Venue="Gesa Stadium",**{"Source Event ID":"200030558055913"})
    stale=page("stale",**{"Pipeline Run ID":"old","Original Title":current["Title"],"Event Date":current["Date"],"Source":"AllEvents","Source Event ID":"200030558054705","Venue":current["Venue"]})
    fake=FakeClient([stale])

    result=sync_week(fake,[current],week="2026-08-17",run_id="current")

    assert result["retained_superseded_identity_count"]==1
    assert result["retained_rows"][0]["source_event_id"]=="200030558054705"
    assert fake.pages[0]["properties"]["Source Event ID"]["select"]["name"]=="200030558054705"
    assert fake.created[0]["Source Event ID"]["rich_text"][0]["text"]["content"]=="200030558055913"

@pytest.mark.parametrize(("field","value"),[
    ("Captain Include","INCLUDE"),("Captain Category","Sports"),("Captain Target","MAIN"),
    ("Captain Title Override","Title"),("Captain Time Override","7p"),
    ("Captains Venue Override","venue-page"),("Captain Description Override","Description"),
    ("Curation Status","REVIEWED"),
])
def test_captain_bearing_retained_row_fails_for_review(field,value):
    stale=page("stale",**{"Pipeline Run ID":"old","Original Title":"Gone","Event Date":"2026-08-12","Source":"AllEvents",field:value})
    with pytest.raises(CurationIntegrityError,match="retained same-week rows require review"):
        sync_week(FakeClient([stale]),[row()],week="2026-08-10",run_id="current")

def test_ambiguous_retained_identity_fails_for_review():
    stale=page("stale",**{"Pipeline Run ID":"old","Original Title":"Class","Event Date":"2026-08-11","Source":"AllEvents","Source Event ID":"old","Venue":"Different Venue"})
    with pytest.raises(CurationIntegrityError,match="retained same-week rows require review"):
        sync_week(FakeClient([stale]),[row()],week="2026-08-10",run_id="current")

class MissingCurrentClient(FakeClient):
    def query_week(self,week):
        return []

def test_current_run_missing_key_still_fails(monkeypatch):
    import src.notion_weekly_curation as curation
    monkeypatch.setattr(curation.time,"sleep",lambda _:None)
    with pytest.raises(CurationIntegrityError,match="incomplete current-run sync"):
        sync_week(MissingCurrentClient(),[row()],week="2026-08-10",run_id="current")

def test_unexpected_current_run_key_fails_immediately():
    unexpected=page("unexpected",**{"Pipeline Run ID":"current","Original Title":"Other","Event Date":"2026-08-12","Source":"AllEvents"})
    with pytest.raises(CurationIntegrityError,match="unexpected current-run"):
        sync_week(FakeClient([unexpected]),[row()],week="2026-08-10",run_id="current")

class MalformedCurrentClient(FakeClient):
    def query_week(self,week):
        pages=super().query_week(week)
        if self.created:
            pages[-1]["properties"]["Venue"]={"type":"rich_text","rich_text":[{"plain_text":"Wrong"}]}
        return pages

def test_malformed_current_pipeline_row_fails():
    with pytest.raises(CurationIntegrityError,match="malformed current-run pipeline rows"):
        sync_week(MalformedCurrentClient(),[row()],week="2026-08-10",run_id="current")

def test_pipeline_unchanged_current_row_gets_marker_only_update():
    item=row(); key=curation_key(item,"2026-08-10")
    seed=FakeClient(); sync_week(seed,[item],week="2026-08-10",run_id="old")
    fake=FakeClient(seed.pages)

    result=sync_week(fake,[item],week="2026-08-10",run_id="current")

    assert result["unchanged_rows"]==1
    assert set(fake.updated[0][1])=={"Last Pipeline Sync","Pipeline Run ID"}
    assert result["current_missing_keys"]==[]
