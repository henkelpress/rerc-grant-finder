from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


APP_VERSION = "0.3.1"
APP_DIR = Path(os.environ.get("RERCIE_APP_ROOT") or (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent))
ASSET_DIR = APP_DIR / "assets"
if not ASSET_DIR.is_dir() and not getattr(sys, "frozen", False):
    ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
LOCAL_KNOWLEDGE_DIR = APP_DIR / "local_knowledge"
PUBLIC_CATALOG_URL = "https://henkelpress.github.io/rerc-grant-finder/data.js"
CATALOG_PREFIXES = ("window.RERC_CATALOG = ", "window.GRANT_EXPLORER_DATA = ")
DEFAULT_MODEL = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
LOCAL_CHAT_URL = os.environ.get("RERCIE_LOCAL_CHAT_URL", "http://127.0.0.1:8788/v1/chat/completions")
LOCAL_HEALTH_URL = os.environ.get("RERCIE_LOCAL_HEALTH_URL", "http://127.0.0.1:8788/health")
LOCAL_MODELS_URL = os.environ.get("RERCIE_LOCAL_MODELS_URL", "http://127.0.0.1:8788/v1/models")
SESSION_TOKEN = os.environ.get("RERCIE_SESSION_TOKEN", "")
EXPECTED_HOST = os.environ.get("RERCIE_EXPECTED_HOST", "127.0.0.1:8789").lower()
EXPECTED_ORIGIN = f"http://{EXPECTED_HOST}"
CENSUS_YEAR = "2023"
MAX_REQUEST_BYTES = 6 * 1024 * 1024

STATE_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05", "California": "06",
    "Colorado": "08", "Connecticut": "09", "Delaware": "10", "District of Columbia": "11",
    "Florida": "12", "Georgia": "13", "Hawaii": "15", "Idaho": "16", "Illinois": "17",
    "Indiana": "18", "Iowa": "19", "Kansas": "20", "Kentucky": "21", "Louisiana": "22",
    "Maine": "23", "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31", "Nevada": "32",
    "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35", "New York": "36",
    "North Carolina": "37", "North Dakota": "38", "Ohio": "39", "Oklahoma": "40", "Oregon": "41",
    "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45", "South Dakota": "46",
    "Tennessee": "47", "Texas": "48", "Utah": "49", "Vermont": "50", "Virginia": "51",
    "Washington": "53", "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
    "American Samoa": "60", "Guam": "66", "Northern Mariana Islands": "69", "Puerto Rico": "72",
    "U.S. Virgin Islands": "78",
}

SYSTEM_PROMPT = """You are RERCie, a careful grant-writing assistant for rural communities.

Use only the facts supplied by the user, the selected funding record, public data returned by the app, and local reference files. Never invent eligibility, deadlines, award amounts, match rules, partners, budgets, letters, or local statistics. Write clear, natural public-facing language with short paragraphs. Mark missing facts as [add local fact] and anything that must be verified as [check official source]. A person must review the draft before submission.
"""


def request_json(url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json", "User-Agent": f"RERCie/{APP_VERSION}"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_public_catalog(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    prefix = next((item for item in CATALOG_PREFIXES if raw.startswith(item)), None)
    if not prefix or not raw.endswith(";"):
        raise ValueError("The public funding file was not in the expected format.")
    catalog = json.loads(raw[len(prefix):-1])
    if "items" in catalog:
        items = catalog.get("items") or []
        return {
            "grants": [item for item in items if str(item.get("item_type", "")).lower() == "funding"],
            "resources": [item for item in items if str(item.get("item_type", "")).lower() == "resource"],
            "counts": catalog.get("counts") or {},
            "updated": catalog.get("updated") or "",
        }
    if "grants" in catalog:
        return catalog
    raise ValueError("The public funding file did not contain funding records.")


def fetch_public_catalog() -> dict[str, Any]:
    request = urllib.request.Request(
        PUBLIC_CATALOG_URL,
        headers={"Accept": "application/javascript,text/plain,*/*", "User-Agent": f"RERCie/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return parse_public_catalog(response.read().decode("utf-8"))


def fetch_census_place_profile(community: str, state: str) -> dict[str, str]:
    community = (community or "").split(",")[0].strip()
    state = (state or "").strip()
    # ACS 5-year place profiles cover states, D.C., and Puerto Rico. The other
    # Island Areas use different Census products and are not queried here.
    if state in {"American Samoa", "Guam", "Northern Mariana Islands", "U.S. Virgin Islands"}:
        return {}
    fips = STATE_FIPS.get(state)
    if not community or not fips:
        return {}
    params = {
        "get": "NAME,DP05_0001E,DP03_0062E,DP03_0128PE",
        "for": "place:*",
        "in": f"state:{fips}",
    }
    url = f"https://api.census.gov/data/{CENSUS_YEAR}/acs/acs5/profile?{urllib.parse.urlencode(params)}"
    try:
        rows = request_json(url, timeout=30)
    except Exception:
        return {}
    if not rows or len(rows) < 2:
        return {}
    headers = rows[0]
    needle = community.lower()
    for row in rows[1:]:
        record = dict(zip(headers, row, strict=False))
        if needle in record.get("NAME", "").lower():
            return {
                "source": f"U.S. Census Bureau ACS {CENSUS_YEAR} 5-year profile API",
                "place": record.get("NAME", ""),
                "population": record.get("DP05_0001E", ""),
                "median_household_income": record.get("DP03_0062E", ""),
                "poverty_rate_percent": record.get("DP03_0128PE", ""),
            }
    return {}


def load_local_knowledge(max_total_chars: int = 32000, max_file_chars: int = 9000) -> str:
    LOCAL_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []
    total = 0
    for path in sorted(LOCAL_KNOWLEDGE_DIR.iterdir()):
        if path.name.lower() == "readme.md" or path.suffix.lower() not in {".md", ".txt", ".csv", ".json"} or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not content:
            continue
        block = f"\n--- Local reference: {path.name} ---\n{content[:max_file_chars]}\n"
        if total + len(block) > max_total_chars:
            break
        chunks.append(block)
        total += len(block)
    return "\n".join(chunks).strip()


def compose_prompt(payload: dict[str, Any], public_profile: dict[str, str], local_knowledge: str) -> str:
    return f"""Create a first-draft grant narrative for human review.

Community: {payload.get('community') or '[add community]'}, {payload.get('state') or '[add state or territory]'}
Project title: {payload.get('projectTitle') or '[add project title]'}
Project summary: {payload.get('projectSummary') or '[add project summary]'}

Selected funding record:
{payload.get('selectedGrant') or '[select a funding source]'}

Match and local capacity:
{payload.get('matchCapacity') or '[add match and capacity facts]'}

Public profile:
{json.dumps(public_profile, indent=2)}

Project notes and uploaded text:
{payload.get('projectNotes') or '[add project notes]'}

Source notes:
{payload.get('sourceNotes') or '[add source notes]'}

Local reference files:
{local_knowledge or '[no local reference files loaded]'}

Return Markdown with these sections: Fit Summary; Project Need; Proposed Work; Community Benefit; Work Plan; Budget and Match Notes; Source and Eligibility Checks; Missing Details. Use plain language. Preserve uncertainty. Mark each unsupported fact [add local fact] or [check official source].
""".strip()


def call_local_writer(prompt: str, model: str) -> str:
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 2400,
        "stream": False,
    }
    data = request_json(LOCAL_CHAT_URL, payload=payload, timeout=300)
    choices = data.get("choices") or []
    return choices[0].get("message", {}).get("content", "").strip() if choices else ""


def call_openai_compatible(prompt: str, endpoint: str, api_key: str, model: str) -> str:
    if not endpoint or not api_key or not model:
        raise ValueError("Endpoint, API key, and model are required for online API mode.")
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    data = request_json(endpoint, payload=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=300)
    choices = data.get("choices") or []
    return choices[0].get("message", {}).get("content", "").strip() if choices else ""


def deterministic_scaffold(payload: dict[str, Any], public_profile: dict[str, str]) -> str:
    community = payload.get("community") or "[add community]"
    state = payload.get("state") or "[add state or territory]"
    title = payload.get("projectTitle") or "[add project title]"
    summary = payload.get("projectSummary") or "[add project summary]"
    grant = payload.get("selectedGrant") or "[select a funding source]"
    match = payload.get("matchCapacity") or "[add match and capacity facts]"
    source = payload.get("sourceNotes") or "[add the official source link and current details]"
    profile = "\n".join(f"- {key.replace('_', ' ').title()}: {value}" for key, value in public_profile.items() if value) or "- [add local data]"
    return f"""# {title}

## Fit Summary

This project may fit the selected funding source because it supports the stated need in {community}, {state}. Confirm the current rules, deadline, match, and allowed costs before using this draft.

{grant}

## Project Need

{community} is seeking support to {summary}

Local facts to review:

{profile}

## Proposed Work

[Add the main tasks, responsible partners, schedule, and deliverables.]

## Community Benefit

[Explain who will benefit and how the project supports outdoor recreation, residents, visitors, local businesses, and public spaces.]

## Work Plan

1. Confirm the scope and partners.
2. Confirm the budget and match.
3. Complete required planning, design, and review steps.
4. Deliver the project.
5. Track results.

## Budget and Match Notes

{match}

## Source and Eligibility Checks

{source}

Check the official source for eligible applicants, eligible work, award size, match, deadline, and required attachments.

## Missing Details

- [add applicant legal name]
- [add project location]
- [add total budget]
- [add committed partners]
- [check official source for the current deadline]
"""


def build_draft(payload: dict[str, Any]) -> dict[str, Any]:
    public_profile = fetch_census_place_profile(payload.get("community", ""), payload.get("state", "")) if payload.get("usePublicData") else {}
    provider = str(payload.get("provider") or "local").lower()
    # Online API mode never reads or sends the private local_knowledge folder.
    local_knowledge = "" if provider == "api" else load_local_knowledge()
    prompt = compose_prompt(payload, public_profile, local_knowledge)
    model = str(payload.get("model") or DEFAULT_MODEL)
    warnings: list[str] = []
    try:
        if provider == "local":
            draft = call_local_writer(prompt, model)
        elif provider == "api":
            draft = call_openai_compatible(prompt, str(payload.get("apiEndpoint") or ""), str(payload.get("apiKey") or ""), str(payload.get("apiModel") or ""))
        else:
            draft = deterministic_scaffold(payload, public_profile)
    except Exception:
        label = "The local writer" if provider == "local" else "The online writer"
        warnings.append(f"{label} could not finish, so RERCie made a fill-in outline instead.")
        draft = deterministic_scaffold(payload, public_profile)
    if not draft.strip():
        warnings.append("RERCie could not make a full draft, so it made a fill-in outline instead.")
        draft = deterministic_scaffold(payload, public_profile)
    return {
        "draft": draft,
        "provider": provider,
        "model": model,
        "publicProfile": public_profile,
        "localKnowledgeChars": len(local_knowledge),
        "warnings": warnings,
        "generatedAt": int(time.time()),
    }


def _paragraph_xml(text: str, style: str | None = None) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    safe = escape(text)
    return f'<w:p>{properties}<w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>'


def build_docx(draft: str, title: str = "RERCie Draft") -> bytes:
    paragraphs: list[str] = []
    for raw_line in (draft or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            paragraphs.append("<w:p/>")
        elif line.startswith("### "):
            paragraphs.append(_paragraph_xml(line[4:], "Heading3"))
        elif line.startswith("## "):
            paragraphs.append(_paragraph_xml(line[3:], "Heading2"))
        elif line.startswith("# "):
            paragraphs.append(_paragraph_xml(line[2:], "Title"))
        elif re.match(r"^[-*]\s+", line):
            paragraphs.append(_paragraph_xml("- " + re.sub(r"^[-*]\s+", "", line)))
        else:
            paragraphs.append(_paragraph_xml(line))
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{''.join(paragraphs)}<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"/></w:sectPr></w:body></w:document>'''
    styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="00573F"/><w:sz w:val="34"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="173F35"/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
    document_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    core_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{escape(title)}</dc:title><dc:creator>RERCie</dc:creator></cp:coreProperties>'''
    app_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>RERCie</Application></Properties>'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types)
        package.writestr("_rels/.rels", root_rels)
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", styles_xml)
        package.writestr("word/_rels/document.xml.rels", document_rels)
        package.writestr("docProps/core.xml", core_xml)
        package.writestr("docProps/app.xml", app_xml)
    return output.getvalue()


HTML_PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RERCie Local Grant-Writing Guide</title>
  <link rel="icon" type="image/jpeg" href="/assets/rercie-otter.jpg">
  <style>
    :root { --green:#00573f; --forest:#173f35; --leaf:#3e7c59; --river:#1b6a8f; --sky:#dceef5; --sun:#f2c14e; --ink:#20312b; --muted:#5d6b66; --line:#d8e0dc; --paper:#fff; --mist:#f3f7f4; --danger:#8b1e1e; }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--mist); font-family:Arial,Helvetica,sans-serif; line-height:1.5; letter-spacing:0; }
    a { color:var(--river); }
    header { padding:24px max(20px,calc((100vw - 1280px)/2)); color:#fff; background:var(--green); border-bottom:5px solid var(--sun); }
    header .brand { display:flex; justify-content:space-between; gap:20px; align-items:center; }
    header .welcome { display:grid; grid-template-columns:minmax(0,1fr) 120px; gap:24px; align-items:center; }
    header .mascot { width:120px; height:168px; object-fit:contain; border:4px solid rgba(255,255,255,.82); border-radius:6px; background:#fff; }
    header h1 { margin:12px 0 6px; font-size:2.25rem; line-height:1.05; }
    header p { max-width:760px; margin:0; color:#e4f1eb; }
    header a { color:#fff; font-weight:700; }
    .privacy { padding:10px max(20px,calc((100vw - 1280px)/2)); color:var(--forest); background:var(--sky); font-size:1rem; }
    .notice { padding:10px max(20px,calc((100vw - 1280px)/2)); color:var(--ink); background:#fff8df; border-bottom:1px solid #e6cf82; font-size:1rem; }
    main { display:grid; grid-template-columns:minmax(300px,430px) minmax(0,1fr); gap:16px; width:min(1320px,100%); margin:0 auto; padding:16px; }
    .panel { padding:18px; border:1px solid var(--line); background:var(--paper); }
    h2 { margin:0 0 8px; font-size:1.12rem; }
    .section-note { margin:0 0 12px; color:var(--muted); font-size:1rem; }
    label { display:block; margin:12px 0 5px; color:var(--forest); font-size:1rem; font-weight:700; }
    input, select, textarea { width:100%; min-height:42px; padding:9px 10px; border:1px solid #aebdb5; border-radius:4px; color:var(--ink); background:#fff; font:inherit; letter-spacing:0; }
    textarea { min-height:96px; resize:vertical; }
    .small { min-height:72px; }
    .check { display:flex; gap:8px; align-items:flex-start; font-weight:400; }
    .check input { width:auto; min-height:0; margin-top:4px; }
    .actions { display:flex; flex-wrap:wrap; gap:9px; margin-top:14px; }
    button { min-height:43px; padding:0 14px; border:2px solid var(--green); border-radius:5px; color:#fff; background:var(--green); font:inherit; font-weight:800; cursor:pointer; }
    button.secondary { border-color:var(--sun); color:#17251f; background:var(--sun); }
    button.quiet { color:var(--green); background:#fff; }
    button:disabled { cursor:wait; opacity:.7; }
    .engine { display:grid; grid-template-columns:minmax(220px,1fr) auto; gap:12px; align-items:end; padding:12px; border-left:5px solid var(--leaf); background:var(--mist); }
    .engine label { margin-top:0; }
    .runtime { align-self:center; padding:7px 10px; border-radius:4px; color:var(--forest); background:#e1eee5; font-size:1rem; font-weight:700; }
    .runtime.offline { color:var(--danger); background:#fdeaea; }
    .advanced { display:none; margin-top:10px; padding:12px; border:1px solid var(--line); background:#fafcfb; }
    .advanced.visible { display:block; }
    .status { margin:12px 0; color:var(--muted); font-size:1rem; }
    .status.warning { color:var(--danger); }
    .output { min-height:570px; padding:18px; border:1px solid var(--line); white-space:pre-wrap; background:#fff; font-family:Consolas,"Courier New",monospace; font-size:1rem; overflow-wrap:anywhere; }
    @media (max-width:900px) { main { grid-template-columns:1fr; } .output { min-height:420px; } }
    @media (max-width:560px) { header .brand,.engine { grid-template-columns:1fr; display:grid; } header .welcome { grid-template-columns:minmax(0,1fr) 88px; gap:12px; } header .mascot { width:88px; height:124px; } main { padding:10px; } .panel { padding:14px; } .actions button { flex:1 1 145px; } }
  </style>
</head>
<body>
  <header>
    <div class="brand"><strong>Recreation Economy <em>for</em> Rural Communities</strong><a href="https://henkelpress.github.io/rerc-grant-finder/" target="_blank" rel="noopener">Open the public explorer</a></div>
    <div class="welcome"><div><h1>Meet RERCie</h1><p>RERCie helps you turn a grant match and your project notes into a first draft. Check every fact before you apply.</p></div><img class="mascot" src="/assets/rercie-otter.jpg" alt="RERCie, a river otter holding a field notebook"></div>

  </header>
  <div class="privacy"><strong>Private by default:</strong> local writing stays on this computer. Census and catalog lookups use public websites. Online API mode sends typed or uploaded project text, selected funding details, and any public Census profile to the provider you choose. It does not read or send files from <code>local_knowledge</code>.</div>
  <div class="notice"><strong>Keep in mind:</strong> RERCie is a community-built grant-writing guide. It is not an EPA grant program. It does not decide who can apply or submit an application for you.</div>
  <main>
    <section class="panel">
      <h2>Tell us about the project</h2>
      <p class="section-note">Start with the facts you know. The draft will mark anything that is missing.</p>
      <label for="community">Community</label><input id="community" placeholder="Example: Taos">
      <label for="state">State or territory</label><select id="state"></select>
      <label for="projectTitle">Project title</label><input id="projectTitle" placeholder="Example: Downtown trail connection">
      <label for="projectSummary">What do you want to do?</label><textarea id="projectSummary" class="small"></textarea>
      <label for="grantSelect">Funding match</label><select id="grantSelect"><option value="">Load the public list</option></select>
      <div class="actions"><button id="loadGrants" class="quiet" type="button">Load funding list</button></div>
      <label for="selectedGrant">Funding details</label><textarea id="selectedGrant" placeholder="Choose a funding match above, or paste the current details here."></textarea>
      <label for="matchCapacity">Match, staff, and partners</label><textarea id="matchCapacity" class="small"></textarea>
      <label for="sourceNotes">Facts to check on the official page</label><textarea id="sourceNotes" class="small" placeholder="Deadline, eligibility, match, award size, and source link"></textarea>
      <label for="fileInput">Add text files</label><input id="fileInput" type="file" multiple accept=".txt,.md,.csv,.json">
      <label for="projectNotes">Notes and file text</label><textarea id="projectNotes"></textarea>
      <label class="check" for="usePublicData"><input id="usePublicData" type="checkbox" checked><span>Look for a basic Census place profile (states, D.C., and Puerto Rico).</span></label>
    </section>
    <section class="panel">
      <div class="engine">
        <div><label for="provider">Writing method</label><select id="provider"><option value="local">Local writing model</option><option value="fallback">Structured outline only</option><option value="api">Online API</option></select></div>
        <span id="runtime" class="runtime">Checking local writer...</span>
      </div>
      <div id="advanced" class="advanced">
        <p class="section-note"><strong>Online privacy:</strong> this sends the form text, uploaded text, selected funding details, and any public Census profile to the provider. Files in <code>local_knowledge</code> stay on this computer.</p>
        <label for="apiEndpoint">API endpoint</label><input id="apiEndpoint" value="https://api.openai.com/v1/chat/completions">
        <label for="apiModel">API model</label><input id="apiModel" placeholder="Provider model name">
        <label for="apiKey">API key</label><input id="apiKey" type="password" autocomplete="off" placeholder="Used for this request only">
      </div>
      <div class="actions">
        <button id="draftButton" class="secondary" type="button">Create first draft</button>
        <button id="downloadDocx" class="quiet" type="button">Export Word</button>
        <button id="downloadMd" class="quiet" type="button">Export Markdown</button>
        <button id="copyDraft" class="quiet" type="button">Copy</button>
      </div>
      <p id="status" class="status" aria-live="polite">Ready.</p>
      <div id="output" class="output" role="region" aria-label="Draft output" tabindex="0">Your first draft will appear here.</div>
    </section>
  </main>
  <script>
    const states = __STATE_OPTIONS__;
    const stateSelect = document.getElementById("state");
    states.forEach((state) => { const option=document.createElement("option"); option.value=state; option.textContent=state||"Choose a state or territory"; stateSelect.appendChild(option); });
    let lastDraft="";
    const status=document.getElementById("status"); const output=document.getElementById("output");
    const sessionToken=new URLSearchParams(location.hash.slice(1)).get("token")||""; history.replaceState(null,"",location.pathname+location.search);
    function apiFetch(url,options={}){ const headers=new Headers(options.headers||{}); headers.set("X-RERCie-Token",sessionToken); return fetch(url,{...options,headers}); }
    function setStatus(message,warning=false){ status.textContent=message; status.className=warning?"status warning":"status"; }
    function collectPayload(){ return {community:document.getElementById("community").value,state:stateSelect.value,projectTitle:document.getElementById("projectTitle").value,projectSummary:document.getElementById("projectSummary").value,selectedGrant:document.getElementById("selectedGrant").value,matchCapacity:document.getElementById("matchCapacity").value,sourceNotes:document.getElementById("sourceNotes").value,projectNotes:document.getElementById("projectNotes").value,usePublicData:document.getElementById("usePublicData").checked,provider:document.getElementById("provider").value,model:"qwen2.5-1.5b-instruct-q4_k_m.gguf",apiEndpoint:document.getElementById("apiEndpoint").value,apiModel:document.getElementById("apiModel").value,apiKey:document.getElementById("apiKey").value}; }
    async function checkRuntime(){ const badge=document.getElementById("runtime"); try{ const response=await apiFetch("/api/runtime"); const data=await response.json(); badge.textContent=data.ready?"Local model ready":"Local model is starting"; badge.className=data.ready?"runtime":"runtime offline"; }catch{ badge.textContent="Could not check local writer"; badge.className="runtime offline"; } }
    async function loadGrants(){ setStatus("Loading the public funding list..."); const response=await apiFetch("/api/grants"); if(!response.ok) throw new Error((await response.json()).error||"The list could not be loaded."); const data=await response.json(); const select=document.getElementById("grantSelect"); select.innerHTML='<option value="">Choose a funding match</option>'; data.grants.forEach((grant,index)=>{ const option=document.createElement("option"); option.value=String(index); option.textContent=`${grant.title||grant.program||"Untitled"} - ${grant.organization||grant.agency||"Organization not listed"}`; option.dataset.grant=JSON.stringify(grant,null,2); select.appendChild(option); }); setStatus(`Loaded ${data.grants.length} funding options. Updated ${data.updated||"date not listed"}.`); }
    document.getElementById("loadGrants").addEventListener("click",()=>loadGrants().catch((error)=>setStatus(`Could not load funding: ${error.message}`,true)));
    document.getElementById("grantSelect").addEventListener("change",(event)=>{ document.getElementById("selectedGrant").value=event.target.selectedOptions[0]?.dataset?.grant||""; });
    document.getElementById("fileInput").addEventListener("change",async(event)=>{ const parts=[]; for(const file of event.target.files){ if(file.size>2000000){ setStatus(`${file.name} is too large. Use a text file under 2 MB.`,true); continue; } parts.push(`\n--- File: ${file.name} ---\n${await file.text()}`); } const notes=document.getElementById("projectNotes"); notes.value=`${notes.value}\n${parts.join("\n")}`.trim(); if(parts.length) setStatus(`Read ${parts.length} file(s).`); });
    document.getElementById("provider").addEventListener("change",(event)=>{ document.getElementById("advanced").classList.toggle("visible",event.target.value==="api"); });
    document.getElementById("draftButton").addEventListener("click",async()=>{ const button=document.getElementById("draftButton"); button.disabled=true; setStatus("Creating a first draft..."); try{ const response=await apiFetch("/api/draft",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(collectPayload())}); const data=await response.json(); if(!response.ok) throw new Error(data.error||"Draft failed."); lastDraft=data.draft; output.textContent=data.draft; setStatus(data.warnings?.length?data.warnings.join(" "):(data.localKnowledgeChars?"Draft ready. Local reference files were used.":"Draft ready."),Boolean(data.warnings?.length)); }catch(error){ setStatus(`Draft failed: ${error.message}`,true); }finally{ button.disabled=false; } });
    function downloadBlob(blob,filename){ const link=document.createElement("a"); link.href=URL.createObjectURL(blob); link.download=filename; link.click(); setTimeout(()=>URL.revokeObjectURL(link.href),1000); }
    function draftFilename(extension){ const raw=document.getElementById("projectTitle").value||"Project"; const safe=raw.normalize("NFKD").replace(/[^\w -]/g,"").trim().replace(/\s+/g,"_").slice(0,60)||"Project"; const now=new Date(); const date=[now.getFullYear(),String(now.getMonth()+1).padStart(2,"0"),String(now.getDate()).padStart(2,"0")].join("-"); return `RERCie_${safe}_Draft_${date}.${extension}`; }
    document.getElementById("downloadMd").addEventListener("click",()=>{ if(!lastDraft){setStatus("Create a draft first.",true);return;} downloadBlob(new Blob([lastDraft],{type:"text/markdown"}),draftFilename("md")); });
    document.getElementById("downloadDocx").addEventListener("click",async()=>{ if(!lastDraft){setStatus("Create a draft first.",true);return;} setStatus("Building the Word file..."); const response=await apiFetch("/api/export-docx",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:lastDraft,title:document.getElementById("projectTitle").value||"RERCie Draft"})}); if(!response.ok){setStatus("The Word file could not be created.",true);return;} downloadBlob(await response.blob(),draftFilename("docx")); setStatus("Word file ready."); });
    document.getElementById("copyDraft").addEventListener("click",async()=>{ if(!lastDraft){setStatus("Create a draft first.",true);return;} await navigator.clipboard.writeText(lastDraft); setStatus("Draft copied."); });
    checkRuntime(); loadGrants().catch(()=>setStatus("The public funding list is not available right now. You can paste funding details instead.",true));
  </script>
</body>
</html>'''.replace("__STATE_OPTIONS__", json.dumps([""] + list(STATE_FIPS.keys())))


class RERCieHandler(BaseHTTPRequestHandler):
    server_version = f"RERCie/{APP_VERSION}"

    def log_message(self, format: str, *args: Any) -> None:
        stream = getattr(sys, "stderr", None)
        if stream and hasattr(stream, "write"):
            try:
                stream.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format % args))
            except (OSError, ValueError):
                pass

    def _authorize(self, require_token: bool = False) -> bool:
        if self.headers.get("Host", "").lower() != EXPECTED_HOST:
            self.send_json({"error": "Local request rejected."}, status=421)
            return False
        if require_token:
            origin = self.headers.get("Origin", "")
            if origin and origin.lower() != EXPECTED_ORIGIN:
                self.send_json({"error": "Local request rejected."}, status=403)
                return False
            provided = self.headers.get("X-RERCie-Token", "")
            if not SESSION_TOKEN or not secrets.compare_digest(provided, SESSION_TOKEN):
                self.send_json({"error": "Local session not authorized."}, status=403)
                return False
        return True

    def _headers(self, status: int, content_type: str, length: int, disposition: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def send_bytes(self, body: bytes, content_type: str, filename: str) -> None:
        self._headers(200, content_type, len(body), f'attachment; filename="{filename}"')
        self.wfile.write(body)

    def send_text(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self._headers(status, "text/html; charset=utf-8", len(encoded))
        self.wfile.write(encoded)

    def read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("The request was empty or too large.")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("The request must be a JSON object.")
        return payload

    def do_GET(self) -> None:
        require_token = self.path == "/health" or self.path.startswith("/api/")
        if not self._authorize(require_token=require_token):
            return
        if self.path in {"/", "/index.html"}:
            self.send_text(HTML_PAGE)
        elif self.path == "/assets/rercie-otter.jpg":
            asset_path = ASSET_DIR / "rercie-otter.jpg"
            if not asset_path.is_file():
                self.send_json({"error": "Not found"}, status=404)
                return
            body = asset_path.read_bytes()
            self._headers(200, "image/jpeg", len(body))
            self.wfile.write(body)
        elif self.path == "/health":
            self.send_json({"status": "ok", "app": "RERCie", "version": APP_VERSION})
        elif self.path == "/api/runtime":
            try:
                health = request_json(LOCAL_HEALTH_URL, timeout=3)
                models = request_json(LOCAL_MODELS_URL, timeout=3)
                model_ids = [str(item.get("id") or "") for item in models.get("data", []) if isinstance(item, dict)]
                ready = str(health.get("status", "")).lower() in {"ok", "ready"} and any(DEFAULT_MODEL in model_id for model_id in model_ids)
                self.send_json({"ready": ready})
            except Exception:
                self.send_json({"ready": False})
        elif self.path == "/api/grants":
            try:
                self.send_json(fetch_public_catalog())
            except Exception as exc:
                self.send_json({"error": html.escape(str(exc))}, status=502)
        else:
            self.send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        if not self._authorize(require_token=True):
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self.send_json({"error": "Use application/json for local requests."}, status=415)
            return
        try:
            payload = self.read_payload()
            if self.path == "/api/draft":
                self.send_json(build_draft(payload))
            elif self.path == "/api/export-docx":
                document = build_docx(str(payload.get("draft") or ""), str(payload.get("title") or "RERCie Draft"))
                self.send_bytes(document, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "RERCie_Draft.docx")
            else:
                self.send_json({"error": "Not found"}, status=404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=400)


def serve(host: str, port: int) -> int:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("RERCie can run only on this computer.")
    if not SESSION_TOKEN:
        raise RuntimeError("RERCie needs a local session token.")
    server = ThreadingHTTPServer((host, port), RERCieHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def smoke() -> int:
    current = parse_public_catalog('window.RERC_CATALOG = {"items":[{"item_type":"Funding","title":"One"},{"item_type":"Resource","title":"Two"}]};')
    assert len(current["grants"]) == 1 and len(current["resources"]) == 1
    legacy = parse_public_catalog('window.GRANT_EXPLORER_DATA = {"grants":[{"title":"Legacy"}]};')
    assert len(legacy["grants"]) == 1
    sample = {"community":"Damascus","state":"Virginia","projectTitle":"Trailhead Wayfinding","projectSummary":"Improve access from downtown to nearby trails.","selectedGrant":"Sample funding record","usePublicData":False,"provider":"fallback"}
    result = build_draft(sample)
    assert "Fit Summary" in result["draft"]
    docx = build_docx(result["draft"], "Smoke Test")
    assert docx.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(docx)) as package:
        assert "word/document.xml" in package.namelist()
    print(json.dumps({"status":"PASS","version":APP_VERSION,"catalog_formats":2,"territories":5,"docx_bytes":len(docx)},indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="RERCie Local Grant-Writing Guide")
    parser.add_argument("--serve", action="store_true", help="start the local web interface")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8789)
    parser.add_argument("--smoke", action="store_true", help="run offline checks")
    args = parser.parse_args()
    if args.smoke:
        return smoke()
    if args.serve:
        return serve(args.host, args.port)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
