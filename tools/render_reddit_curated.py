"""Render a frozen Weekly Curation inventory without harvesting or publishing."""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path

from src.notion_weekly_curation import NotionCurationClient
from src.mission_control import SourceHealthSummary
from src.mission_run_summary import write_production_mission_control
from src.program_intelligence import group_editorial_programs
from src.publisher_audit import default_audit_path, write_publisher_audit
from src.publisher_editorial import COMPLETED_REJECTION_REASONS, community_events, main_events, rejected_events, review_events
from src.publishing_contract import PublishingProfile
from src.reddit_renderer import default_community_artifact_path, default_main_artifact_path, write_reddit_artifact
from src.weekly_curation_workflow import WEEKLY_CURATION_DATA_SOURCE_ID, WEEKLY_CURATION_DATABASE_URL, load_curated_editorial


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week-start",type=date.fromisoformat,required=True)
    parser.add_argument("--curation-data-source-id",default=WEEKLY_CURATION_DATA_SOURCE_ID)
    parser.add_argument("--curation-inventory",type=Path)
    parser.add_argument("--curation-sync-audit",type=Path)
    parser.add_argument("--output-main",type=Path)
    parser.add_argument("--output-community",type=Path)
    parser.add_argument("--output-audit",type=Path)
    parser.add_argument("--excel-fallback",type=Path,help="Explicit fallback only; not yet supported by this command")
    args=parser.parse_args()
    if args.excel_fallback: parser.error("Excel fallback requires a separately reviewed explicit fallback workflow")
    token=os.environ.get("NOTION_TOKEN","").strip()
    if not token: parser.error("curated render requires NOTION_TOKEN; autonomous fallback is forbidden")
    root=Path("artifacts/review/notion_curation")
    inventory=args.curation_inventory or root/f"Weekly_Curation_Inventory_{args.week_start.isoformat()}.json"
    audit=args.curation_sync_audit or root/f"Weekly_Curation_Sync_Audit_{args.week_start.isoformat()}.json"
    client=NotionCurationClient(token,args.curation_data_source_id)
    try: editorial=load_curated_editorial(client,week=args.week_start.isoformat(),inventory_path=inventory,audit_path=audit)
    finally: client.close()
    profile=PublishingProfile.load()
    main_publishable=main_events(editorial); community_publishable=community_events(editorial)
    main=group_editorial_programs(main_publishable); community=group_editorial_programs(community_publishable)
    footnote="*Curated in Notion Weekly Curation; source attribution retained per event.*"
    write_reddit_artifact(main,args.output_main or default_main_artifact_path(),footnote=footnote,category_order=profile.category_order)
    write_reddit_artifact(community,args.output_community or default_community_artifact_path(),footnote=footnote,category_order=profile.category_order)
    write_publisher_audit(editorial,args.output_audit or default_audit_path(),category_order=profile.category_order)
    sync_audit=json.loads(audit.read_text(encoding="utf-8")); evidence=sync_audit.get("production_evidence") or {}
    if not evidence: raise RuntimeError("curated readiness requires frozen production evidence from prepare mode")
    review=review_events(editorial); rejected=rejected_events(editorial)
    completed=[item for item in rejected if item.editorial_reason in COMPLETED_REJECTION_REASONS]
    unresolved=[item for item in rejected if item.editorial_reason not in COMPLETED_REJECTION_REASONS]
    blockers=[item for item in review if item.editorial_reason!="missing_or_unknown_category"]
    editorial_reviews=[item for item in review if item.editorial_reason=="missing_or_unknown_category"]
    main_output=args.output_main or default_main_artifact_path(); community_output=args.output_community or default_community_artifact_path(); audit_output=args.output_audit or default_audit_path()
    sources=[SourceHealthSummary(source=item["source_name"],status=item["status"],harvested=int(item.get("event_count",0)),reason=item.get("reason"),duration_ms=(evidence.get("source_durations_ms") or {}).get(item["source_name"])) for item in evidence.get("sources",[])]
    mission_report,mission_outputs=write_production_mission_control(week_start=args.week_start.isoformat(),production_status=evidence.get("production_status","UNKNOWN"),source_health=sources,source_durations_ms={},counts={"harvested":sync_audit["inventory_count"],"deduplicated":sync_audit["inventory_count"],"weekly":len(editorial),"main":len(main_publishable),"main_programs":len(main),"community":len(community_publishable),"community_programs":len(community),"review":len(review),"publication_blockers":len(blockers),"editorial_reviews":len(editorial_reviews),"rejected":len(rejected),"completed_rejections":len(completed),"unresolved_rejections":len(unresolved)},artifacts={"main_reddit":main_output,"community_reddit":community_output,"publisher_audit":audit_output,"curation_inventory":inventory,"curation_sync_audit":audit},warnings=evidence.get("warnings",[]))
    if not mission_report.ready_to_publish: raise RuntimeError(f"Mission Control held curated artifacts: {mission_report.captain_summary}")
    print(f"Weekly Curation: {WEEKLY_CURATION_DATABASE_URL}")
    print(f"Mission Control: READY TO PUBLISH; archive: {mission_outputs['archive_dashboard'].parent}")
    print("Curated artifacts ready for final human inspection; stopped before publication")
    return 0

if __name__=="__main__": raise SystemExit(main())
