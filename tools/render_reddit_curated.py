"""Render a frozen Weekly Curation inventory without harvesting or publishing."""
from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path

from src.notion_weekly_curation import NotionCurationClient
from src.program_intelligence import group_editorial_programs
from src.publisher_audit import default_audit_path, write_publisher_audit
from src.publisher_editorial import community_events, main_events
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
    main=group_editorial_programs(main_events(editorial)); community=group_editorial_programs(community_events(editorial))
    footnote="*Curated in Notion Weekly Curation; source attribution retained per event.*"
    write_reddit_artifact(main,args.output_main or default_main_artifact_path(),footnote=footnote,category_order=profile.category_order)
    write_reddit_artifact(community,args.output_community or default_community_artifact_path(),footnote=footnote,category_order=profile.category_order)
    write_publisher_audit(editorial,args.output_audit or default_audit_path(),category_order=profile.category_order)
    print(f"Weekly Curation: {WEEKLY_CURATION_DATABASE_URL}")
    print("Curated artifacts rendered; stopped before publication")
    return 0

if __name__=="__main__": raise SystemExit(main())
