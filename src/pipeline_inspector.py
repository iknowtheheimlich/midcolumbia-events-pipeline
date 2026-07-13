"""Standalone HTML inspection report for one event across pipeline stages.

Attempt_44_PipelineInspector

The inspector observes existing pipeline objects. It does not re-run, reinterpret, or
modify intelligence decisions.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from html import escape
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_INSPECTOR_PATH = Path("artifacts") / "inspector" / "Pipeline_Inspector.html"


def matches_query(value: Any, query: str) -> bool:
    """Return whether an event-like value contains the case-insensitive query."""
    needle = query.strip().casefold()
    if not needle:
        raise ValueError("pipeline inspector query must not be empty")
    payload = _json_safe(value)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).casefold()
    return needle in text


def matching_rows(values: Iterable[Any], query: str) -> list[Any]:
    """Return matching rows while preserving stage order."""
    return [value for value in values if matches_query(value, query)]


def render_pipeline_inspector(
    query: str,
    stages: Mapping[str, Iterable[Any]],
    *,
    rendered_lines: Iterable[str] = (),
) -> str:
    """Render one deterministic, dependency-free HTML inspection report."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("pipeline inspector query must not be empty")

    sections: list[str] = []
    total_matches = 0
    for stage_name, values in stages.items():
        rows = matching_rows(values, clean_query)
        total_matches += len(rows)
        sections.append(_render_stage(stage_name, rows))

    lines = [line for line in rendered_lines if clean_query.casefold() in line.casefold()]
    if lines:
        sections.append(
            '<section><h2>Final Reddit lines</h2><div class="count">'
            f"{len(lines)} match(es)</div>"
            + "".join(f"<pre>{escape(line)}</pre>" for line in lines)
            + "</section>"
        )

    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCEI Pipeline Inspector</title>
<style>
body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.45;background:#f5f5f5;color:#171717}
header,section{background:white;border:1px solid #ddd;border-radius:8px;padding:1rem 1.25rem;margin-bottom:1rem}
h1,h2{margin:.2rem 0 .5rem}.count{color:#555;margin-bottom:.75rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f0f0;padding:.8rem;border-radius:5px;border-left:4px solid #777}details{margin:.65rem 0}summary{cursor:pointer;font-weight:650}.empty{color:#777;font-style:italic}
</style>
</head>
<body>
<header>
<h1>MCEI Pipeline Inspector</h1>
<p><strong>Query:</strong> """ + escape(clean_query) + """</p>
<p><strong>Stage matches:</strong> """ + str(total_matches) + """</p>
</header>
""" + "".join(sections) + """
</body>
</html>
"""


def write_pipeline_inspector(
    query: str,
    stages: Mapping[str, Iterable[Any]],
    output_path: Path = DEFAULT_INSPECTOR_PATH,
    *,
    rendered_lines: Iterable[str] = (),
) -> Path:
    """Write an inspector artifact outside fixture directories."""
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated inspector artifacts must remain separate from fixtures")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_pipeline_inspector(query, stages, rendered_lines=rendered_lines),
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def _render_stage(stage_name: str, rows: list[Any]) -> str:
    if not rows:
        body = '<p class="empty">No matching records.</p>'
    else:
        blocks = []
        for index, row in enumerate(rows, start=1):
            payload = json.dumps(_json_safe(row), indent=2, ensure_ascii=False, sort_keys=True, default=str)
            blocks.append(
                f"<details{' open' if index == 1 else ''}><summary>Record {index}</summary>"
                f"<pre>{escape(payload)}</pre></details>"
            )
        body = "".join(blocks)
    return (
        f"<section><h2>{escape(stage_name)}</h2>"
        f'<div class="count">{len(rows)} match(es)</div>{body}</section>'
    )


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted((_json_safe(item) for item in value), key=lambda item: str(item))
    return value
