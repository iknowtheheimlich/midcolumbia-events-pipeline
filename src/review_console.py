"""Generate a single-file editorial review console from Review_Training.json."""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
from typing import Any, Iterable

from src.publishing_contract import PublishingProfile

_TITLE_SPLIT_RE = re.compile(r"\s+\|\s+")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
_SPACE_RE = re.compile(r"\s+")


def published_lookup(paths: Iterable[Path]) -> dict[str, dict[str, str]]:
    """Return normalized-title matches from already-edited Reddit artifacts."""
    result: dict[str, dict[str, str]] = {}
    category: str | None = None
    categories = set(PublishingProfile.load().category_order)
    for path in paths:
        if not path:
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            heading = line.lstrip("#").strip() if line.startswith("#") else None
            if heading in categories:
                category = heading
                continue
            if not category or " | " not in line or line.startswith("#"):
                continue
            title = _clean_title(_TITLE_SPLIT_RE.split(line, maxsplit=1)[0])
            if title:
                result[_key(title)] = {
                    "title": title,
                    "category": category,
                    "source_post": str(path),
                }
    return result


def build_review_console(
    training_path: Path,
    output_path: Path,
    *,
    published_paths: Iterable[Path] = (),
) -> Path:
    payload = json.loads(training_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("review training artifact must contain a records list")

    matches = published_lookup(published_paths)
    prepared: list[dict[str, Any]] = []
    for record in records:
        copied = dict(record)
        match = matches.get(_key(str(record.get("title") or "")))
        copied["published_match"] = match
        prepared.append(copied)

    profile = PublishingProfile.load()
    data = json.dumps(
        {
            "records": prepared,
            "categories": profile.category_order,
            "source": str(training_path),
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_document(data), encoding="utf-8")
    return output_path


def _document(data: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Editorial Review Console</title>
<style>
:root {{ color-scheme: dark; font-family: Segoe UI, system-ui, sans-serif; }}
body {{ margin:0; background:#101418; color:#edf2f7; }}
header {{ position:sticky; top:0; z-index:2; background:#172027; padding:12px 18px; border-bottom:1px solid #34404a; display:flex; gap:16px; align-items:center; }}
main {{ max-width:1100px; margin:0 auto; padding:20px; }}
.card {{ background:#182128; border:1px solid #34404a; border-radius:12px; padding:18px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.full {{ grid-column:1 / -1; }}
label {{ display:block; font-size:12px; color:#aebbc6; margin-bottom:5px; }}
input, select, textarea {{ width:100%; box-sizing:border-box; background:#0f1519; color:#fff; border:1px solid #44515c; border-radius:7px; padding:9px; }}
textarea {{ min-height:86px; }}
.meta {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 14px; }}
.badge {{ background:#26323b; border-radius:999px; padding:5px 9px; font-size:12px; }}
.actions {{ display:flex; gap:10px; margin-top:18px; flex-wrap:wrap; }}
button {{ border:0; border-radius:8px; padding:10px 15px; font-weight:700; cursor:pointer; }}
.primary {{ background:#69c0ff; color:#081018; }}
.secondary {{ background:#34404a; color:#fff; }}
.danger {{ background:#ff8a80; color:#1c0806; }}
.match {{ background:#173b2c; border:1px solid #2e7656; padding:10px; border-radius:8px; margin-bottom:14px; }}
small {{ color:#9cabb7; }}
a {{ color:#8acbff; }}
@media (max-width:760px) {{ .grid {{ grid-template-columns:1fr; }} .full {{ grid-column:auto; }} }}
</style>
</head>
<body>
<header>
<strong>Editorial Review Console</strong>
<span id="progress"></span>
<button class="secondary" onclick="exportCorrections()">Export corrections</button>
</header>
<main><div id="app"></div></main>
<script id="review-data" type="application/json">{data}</script>
<script>
const DATA = JSON.parse(document.getElementById('review-data').textContent);
const state = JSON.parse(localStorage.getItem('midcolumbia-review-state') || '{{}}');
let index = Number(localStorage.getItem('midcolumbia-review-index') || 0);
const records = DATA.records;

function esc(value) {{
  return String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
}}
function current() {{ return records[index]; }}
function decisionFor(r) {{
  if (state[r.fingerprint]) return state[r.fingerprint];
  const match = r.published_match;
  return {{
    corrected_title: match?.title || r.title || '',
    corrected_venue: r.venue || '',
    corrected_city: r.city || '',
    corrected_host: r.host || '',
    correct_category: match?.category || r.current_category || '',
    decision: match ? 'INCLUDE' : '',
    notes: '',
  }};
}}
function saveForm() {{
  const r = current(); if (!r) return;
  state[r.fingerprint] = {{
    corrected_title: document.getElementById('title').value.trim(),
    corrected_venue: document.getElementById('venue').value.trim(),
    corrected_city: document.getElementById('city').value.trim(),
    corrected_host: document.getElementById('host').value.trim(),
    correct_category: document.getElementById('category').value,
    decision: document.getElementById('decision').value,
    notes: document.getElementById('notes').value.trim(),
  }};
  localStorage.setItem('midcolumbia-review-state', JSON.stringify(state));
}}
function render() {{
  const r = current();
  document.getElementById('progress').textContent = `${{index + 1}} / ${{records.length}} · ${{Object.keys(state).length}} saved`;
  if (!r) {{ document.getElementById('app').innerHTML = '<div class="card">Review complete.</div>'; return; }}
  const d = decisionFor(r);
  const options = ['<option value=""></option>', ...DATA.categories.map(c => `<option ${{c===d.correct_category?'selected':''}}>${{esc(c)}}</option>`)].join('');
  const match = r.published_match ? `<div class="match"><strong>Found in this week’s post</strong><br>${{esc(r.published_match.title)}} → ${{esc(r.published_match.category)}}</div>` : '';
  document.getElementById('app').innerHTML = `<div class="card">
    ${{match}}
    <div class="meta">
      <span class="badge">${{esc(r.start_date)}} ${{esc(r.start_time)}}</span>
      <span class="badge">${{esc(r.editorial_reason)}}</span>
      <span class="badge">${{esc(r.geographic_scope)}}</span>
      <span class="badge">Source: ${{esc(r.source)}}</span>
      ${{(r.duplicate_sources||[]).map(s=>`<span class="badge">Also: ${{esc(s)}}</span>`).join('')}}
    </div>
    <div class="grid">
      <div class="full"><label>1. Title</label><input id="title" value="${{esc(d.corrected_title)}}"></div>
      <div><label>2. Location / venue</label><input id="venue" value="${{esc(d.corrected_venue)}}"></div>
      <div><label>City</label><input id="city" value="${{esc(d.corrected_city)}}"></div>
      <div class="full"><label>3. Host / publisher</label><input id="host" value="${{esc(d.corrected_host)}}"></div>
      <div><label>4. Category</label><select id="category">${{options}}</select></div>
      <div><label>5. Decision</label><select id="decision">
        <option value=""></option><option ${{d.decision==='INCLUDE'?'selected':''}}>INCLUDE</option><option ${{d.decision==='EXCLUDE'?'selected':''}}>EXCLUDE</option><option ${{d.decision==='UNSURE'?'selected':''}}>UNSURE</option>
      </select></div>
      <div class="full"><label>Description / source context</label><textarea readonly>${{esc(r.description || '')}}</textarea></div>
      <div class="full"><label>Your notes</label><textarea id="notes">${{esc(d.notes)}}</textarea></div>
    </div>
    <p><a href="${{esc(r.publication_url)}}" target="_blank" rel="noopener">Open source event</a></p>
    <div class="actions">
      <button class="secondary" onclick="previous()">Previous</button>
      <button class="primary" onclick="next()">Save & next</button>
      <button class="danger" onclick="excludeAndNext()">Exclude & next</button>
    </div>
  </div>`;
}}
function next() {{ saveForm(); index=Math.min(index+1, records.length-1); localStorage.setItem('midcolumbia-review-index', index); render(); }}
function previous() {{ saveForm(); index=Math.max(index-1,0); localStorage.setItem('midcolumbia-review-index', index); render(); }}
function excludeAndNext() {{ document.getElementById('decision').value='EXCLUDE'; next(); }}
function exportCorrections() {{
  saveForm();
  const corrections = Object.entries(state).map(([fingerprint,d]) => ({{
    fingerprint,
    action: 'EDITORIAL',
    decision: d.decision,
    corrected_title: d.corrected_title,
    corrected_venue: d.corrected_venue,
    corrected_city: d.corrected_city,
    corrected_host: d.corrected_host,
    correct_category: d.correct_category,
    notes: d.notes,
  }}));
  const blob = new Blob([JSON.stringify({{schema_version:1, corrections}}, null, 2)+'\n'], {{type:'application/json'}});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='Review_Corrections.json'; a.click(); URL.revokeObjectURL(a.href);
}}
render();
</script>
</body>
</html>
"""


def _clean_title(value: str) -> str:
    value = _MARKDOWN_LINK_RE.sub(r"\1", value)
    return _SPACE_RE.sub(" ", value.strip()).strip("-* ")


def _key(value: str) -> str:
    return _SPACE_RE.sub(" ", _clean_title(value).casefold()).strip()
