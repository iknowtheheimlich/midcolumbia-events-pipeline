"""Build actionable Mission 002 review-queue artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from src.review_triage import build_review_triage

DEFAULT_INPUT = Path("artifacts/review/Review_Training.json")
DEFAULT_OUTPUT_DIR = Path("artifacts/review/triage")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    triage, paths = build_review_triage_from_file(args.input, args.output_dir)
    print(f"Review records: {triage['record_count']}")
    print(f"Publication blockers: {triage['publication_blockers']}")
    print(f"Editorial reviews: {triage['editorial_reviews']}")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


def build_review_triage_from_file(
    input_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Path]]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "records" not in payload:
        raise ValueError("review training artifact must contain an object list at 'records'")
    records = payload["records"]
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("review training artifact must contain an object list at 'records'")

    triage = build_review_triage(records)
    return triage, write_review_triage(triage, output_dir)


def write_review_triage(triage: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "Review_Triage.json"
    csv_path = output_dir / "Review_Triage.csv"
    report_path = output_dir / "Review_Triage.txt"

    json_path.write_text(json.dumps(triage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = [
        "severity", "entity_type", "reason", "source", "start_date", "title",
        "venue", "city", "current_category", "category_reason", "publication_url", "fingerprint",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in triage["records"]:
            writer.writerow({field: record.get(field) for field in fields})

    lines = [
        "Mission 002 Review Triage",
        "=========================",
        "",
        f"Review records: {triage['record_count']}",
        f"Publication blockers: {triage['publication_blockers']}",
        f"Editorial reviews: {triage['editorial_reviews']}",
        "",
        "BY REASON",
        "---------",
    ]
    lines.extend(f"{key}: {value}" for key, value in triage["by_reason"].items())
    lines.extend(["", "BY ENTITY TYPE", "--------------"])
    lines.extend(f"{key}: {value}" for key, value in triage["by_entity_type"].items())
    lines.extend(["", "BY SOURCE", "---------"])
    lines.extend(f"{key}: {value}" for key, value in triage["by_source"].items())

    for severity in ("PUBLICATION_BLOCKER", "EDITORIAL_REVIEW"):
        lines.extend(["", severity, "-" * len(severity)])
        matching = [item for item in triage["records"] if item["severity"] == severity]
        for item in matching:
            location = ", ".join(value for value in (item["venue"], item["city"]) if value)
            lines.append(
                f"{item['start_date']} | {item['source']} | {item['reason']} | {item['title']}"
                + (f" | {location}" if location else "")
            )
            if item["publication_url"]:
                lines.append(f"  {item['publication_url']}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "report": report_path}


if __name__ == "__main__":
    raise SystemExit(main())
