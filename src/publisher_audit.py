"""Audit summaries for dual Reddit publication outputs.

Attempt_35_DualPublisher
Attempt_38_CategoryIntelligence
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

from src.publisher_editorial import EditorialEvent


def render_publisher_audit(
    events: Iterable[EditorialEvent],
    *,
    category_order: Sequence[str],
) -> str:
    rows = list(events)
    disposition_counts = Counter(event.publication_disposition for event in rows)
    target_counts = Counter(event.publication_target for event in rows)
    category_counts = Counter(event.semantic_category or "UNCLASSIFIED" for event in rows)

    lines = [
        "Publisher Audit",
        "===============",
        "",
        f"Weekly editorial events: {len(rows)}",
        f"Auto-published: {disposition_counts['AUTO_PUBLISH']}",
        f"Review: {disposition_counts['REVIEW']}",
        f"Rejected: {disposition_counts['REJECT']}",
        "",
        "Publication targets:",
    ]
    for target in ("MAIN", "COMMUNITY", "BOTH", "REVIEW", "SUPPRESS"):
        lines.append(f"  {target}: {target_counts[target]}")

    lines.extend(["", "Categories:"])
    for category in category_order:
        lines.append(f"  {category}: {category_counts[category]}")
    if category_counts["UNCLASSIFIED"]:
        lines.append(f"  UNCLASSIFIED: {category_counts['UNCLASSIFIED']}")

    category_reasons = Counter(
        event.category_reason or "no_category_explanation"
        for event in rows
        if event.semantic_category
    )
    if category_reasons:
        lines.extend(["", "Category decisions:"])
        for reason, count in sorted(category_reasons.items()):
            lines.append(f"  {reason}: {count}")

    review_reasons = Counter(
        event.editorial_reason or "unspecified"
        for event in rows
        if event.publication_disposition == "REVIEW"
    )
    if review_reasons:
        lines.extend(["", "Review reasons:"])
        for reason, count in sorted(review_reasons.items()):
            lines.append(f"  {reason}: {count}")

    return "\n".join(lines) + "\n"


def write_publisher_audit(
    events: Iterable[EditorialEvent],
    output_path: Path,
    *,
    category_order: Sequence[str],
) -> Path:
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated publisher audit must remain separate from fixtures")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_publisher_audit(events, category_order=category_order),
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def default_audit_path() -> Path:
    return Path("artifacts") / "reddit" / "Publisher_Audit.txt"
