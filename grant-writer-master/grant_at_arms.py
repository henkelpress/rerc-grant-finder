from __future__ import annotations

import argparse
import html
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
LOCAL_KNOWLEDGE_DIR = APP_DIR / "local_knowledge"
PUBLIC_GRANTS_URL = "https://henkelpress.github.io/rerc-grant-finder/data.js"
JSON_PREFIX = "window.GRANT_EXPLORER_DATA = "
DEFAULT_MODEL = "gemma3:4b"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
CENSUS_YEAR = "2023"

STATE_FIPS = {
    "Alabama": "01",
    "Alaska": "02",
    "Arizona": "04",
    "Arkansas": "05",
    "California": "06",
    "Colorado": "08",
    "Connecticut": "09",
    "Delaware": "10",
    "District of Columbia": "11",
    "Florida": "12",
    "Georgia": "13",
    "Hawaii": "15",
    "Idaho": "16",
    "Illinois": "17",
    "Indiana": "18",
    "Iowa": "19",
    "Kansas": "20",
    "Kentucky": "21",
    "Louisiana": "22",
    "Maine": "23",
    "Maryland": "24",
    "Massachusetts": "25",
    "Michigan": "26",
    "Minnesota": "27",
    "Mississippi": "28",
    "Missouri": "29",
    "Montana": "30",
    "Nebraska": "31",
    "Nevada": "32",
    "New Hampshire": "33",
    "New Jersey": "34",
    "New Mexico": "35",
    "New York": "36",
    "North Carolina": "37",
    "North Dakota": "38",
    "Ohio": "39",
    "Oklahoma": "40",
    "Oregon": "41",
    "Pennsylvania": "42",
    "Rhode Island": "44",
    "South Carolina": "45",
    "South Dakota": "46",
    "Tennessee": "47",
    "Texas": "48",
    "Utah": "49",
    "Vermont": "50",
    "Virginia": "51",
    "Washington": "53",
    "West Virginia": "54",
    "Wisconsin": "55",
    "Wyoming": "56",
}

SYSTEM_PROMPT = """You are Grant-at-Arms, a practical grant-writing assistant for rural communities.

Use only the information provided by the user, selected grant records, public data returned by the app, and local reference files supplied by the user.

Do not invent eligibility, deadlines, award amounts, match rules, partners, letters of support, budgets, or local statistics.

Write in clear public-facing language. Use short paragraphs. Prefer specific local facts over generic claims.

Flag missing facts as placeholders. Tell the user what must be checked against the current grant source before submission.
"""


def request_json(url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json"}
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=data, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_public_grants() -> dict[str, Any]:
    request = urllib.request.Request(PUBLIC_GRANTS_URL, headers={"Accept": "application/javascript,text/plain,*/*"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8").strip()
    if not raw.startswith(JSON_PREFIX) or not raw.endswith(";"):
        raise ValueError("The public grant data file was not in the expected format.")
    return json.loads(raw[len(JSON_PREFIX) : -1])


def fetch_census_place_profile(community: str, state: str) -> dict[str, str]:
    community = (community or "").split(",")[0].strip()
    state = (state or "").strip()
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
    best = None
    needle = community.lower()
    for row in rows[1:]:
        record = dict(zip(headers, row, strict=False))
        name = record.get("NAME", "")
        lower_name = name.lower()
        if lower_name.startswith(needle + " ") or needle in lower_name:
            best = record
            break
    if not best:
        return {}

    return {
        "source": f"U.S. Census Bureau ACS {CENSUS_YEAR} 5-year profile API",
        "place": best.get("NAME", ""),
        "population": best.get("DP05_0001E", ""),
        "median_household_income": best.get("DP03_0062E", ""),
        "poverty_rate_percent": best.get("DP03_0128PE", ""),
    }


def load_local_knowledge(max_total_chars: int = 32000, max_file_chars: int = 9000) -> str:
    LOCAL_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []
    total = 0
    for path in sorted(LOCAL_KNOWLEDGE_DIR.iterdir()):
        if path.name.lower() == "readme.md":
            continue
        if path.suffix.lower() not in {".md", ".txt", ".csv", ".json"} or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        text = text.strip()
        if not text:
            continue
        snippet = text[:max_file_chars]
        block = f"\n--- Local reference: {path.name} ---\n{snippet}\n"
        if total + len(block) > max_total_chars:
            break
        chunks.append(block)
        total += len(block)
    return "\n".join(chunks).strip()


def compose_prompt(payload: dict[str, Any], public_profile: dict[str, str], local_knowledge: str) -> str:
    selected_grant = payload.get("selectedGrant") or ""
    community = payload.get("community") or ""
    state = payload.get("state") or ""
    project_title = payload.get("projectTitle") or ""
    project_summary = payload.get("projectSummary") or ""
    project_notes = payload.get("projectNotes") or ""
    source_notes = payload.get("sourceNotes") or ""
    match_capacity = payload.get("matchCapacity") or "Not provided"

    return f"""
Draft a grant narrative package for human review.

Community:
{community}, {state}

Project title:
{project_title}

Project summary:
{project_summary}

Selected grant record:
{selected_grant}

Match or local capacity:
{match_capacity}

Public profile:
{json.dumps(public_profile, indent=2)}

User notes and uploaded text:
{project_notes}

Grant source notes:
{source_notes}

Local reference files:
{local_knowledge}

Return Markdown with these sections:

1. Fit Summary
2. Project Need
3. Proposed Work
4. Community Benefit
5. Work Plan
6. Budget and Match Notes
7. Source and Eligibility Checks
8. Missing Details

Use plain language. Mark any uncertain item as [check source] or [add local fact].
""".strip()


def call_ollama(prompt: str, model: str) -> str:
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.25},
    }
    data = request_json(OLLAMA_CHAT_URL, payload=payload, timeout=180)
    return data.get("message", {}).get("content", "").strip()


def call_openai_compatible(prompt: str, endpoint: str, api_key: str, model: str) -> str:
    if not endpoint or not api_key or not model:
        raise ValueError("Endpoint, API key, and model are required for API mode.")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    data = request_json(endpoint, payload=payload, headers=headers, timeout=180)
    choices = data.get("choices") or []
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "").strip()


def deterministic_scaffold(payload: dict[str, Any], public_profile: dict[str, str]) -> str:
    community = payload.get("community") or "[add community]"
    state = payload.get("state") or "[add state]"
    project_title = payload.get("projectTitle") or "[add project title]"
    project_summary = payload.get("projectSummary") or "[add project summary]"
    selected_grant = payload.get("selectedGrant") or "[select grant]"
    match_capacity = payload.get("matchCapacity") or "[add match capacity]"
    source_notes = payload.get("sourceNotes") or "[add source notes]"

    profile_lines = "\n".join(f"- {key}: {value}" for key, value in public_profile.items() if value) or "- [add local data]"

    return f"""# Draft Grant Narrative

## Fit Summary

{project_title} may fit the selected grant because it supports the stated community need in {community}, {state}. Confirm the current eligibility rules, deadline, match requirements, and allowable costs before using this draft.

Selected grant context:

{selected_grant}

## Project Need

{community} is seeking support for {project_summary}

Local data to check:

{profile_lines}

## Proposed Work

The project team will complete the work described in the project notes. Add the main tasks, responsible partners, schedule, and deliverables here.

## Community Benefit

Describe who benefits, how the project supports rural outdoor recreation, and how it helps local businesses, residents, visitors, and public spaces.

## Work Plan

1. Confirm scope and partners.
2. Confirm budget and match.
3. Complete required design, planning, or environmental steps.
4. Deliver the project.
5. Track outcomes after completion.

## Budget and Match Notes

Match capacity: {match_capacity}

Add cost categories, local match sources, in-kind support, and any costs that the grant source does not allow.

## Source and Eligibility Checks

{source_notes}

Before submission, check the current grant source for:

1. Eligible applicants.
2. Eligible activities.
3. Award range.
4. Match.
5. Deadline.
6. Required attachments.

## Missing Details

1. [add applicant legal name]
2. [add project location]
3. [add total budget]
4. [add committed partners]
5. [add source-confirmed deadline]
"""


def build_draft(payload: dict[str, Any]) -> dict[str, Any]:
    public_profile = fetch_census_place_profile(payload.get("community", ""), payload.get("state", "")) if payload.get("usePublicData") else {}
    local_knowledge = load_local_knowledge()
    prompt = compose_prompt(payload, public_profile, local_knowledge)
    provider = (payload.get("provider") or "fallback").lower()
    model = payload.get("model") or DEFAULT_MODEL
    warnings: list[str] = []

    if provider == "ollama":
        try:
            draft = call_ollama(prompt, model)
        except Exception as exc:
            warnings.append(f"Ollama was not available, so the app returned the structured fallback. Details: {type(exc).__name__}: {exc}")
            draft = deterministic_scaffold(payload, public_profile)
    elif provider == "api":
        try:
            draft = call_openai_compatible(
                prompt,
                endpoint=payload.get("apiEndpoint") or "",
                api_key=payload.get("apiKey") or "",
                model=payload.get("apiModel") or "",
            )
        except Exception as exc:
            warnings.append(f"The API request failed, so the app returned the structured fallback. Details: {type(exc).__name__}: {exc}")
            draft = deterministic_scaffold(payload, public_profile)
    else:
        draft = deterministic_scaffold(payload, public_profile)

    if not draft.strip():
        warnings.append("The model returned an empty draft, so the app returned the structured fallback.")
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


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Grant-at-Arms</title>
  <style>
    :root {
      --ink: #1b1b1b;
      --muted: #58655d;
      --green: #2e6f40;
      --green-dark: #17412a;
      --green-soft: #e7f1e7;
      --gold: #f9c642;
      --line: #d8e2d8;
      --paper: #f7f8f4;
      --panel: #ffffff;
      --danger: #8b1e1e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }
    header {
      padding: 28px min(5vw, 56px);
      color: #fff;
      background: linear-gradient(135deg, var(--green-dark), var(--green));
    }
    header p, header h1 { margin: 0; }
    header h1 { max-width: 900px; margin-top: 6px; font-size: clamp(2rem, 5vw, 4rem); line-height: 1; }
    header p { max-width: 760px; margin-top: 12px; color: rgba(255,255,255,.9); }
    main {
      display: grid;
      grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
      gap: 18px;
      padding: 18px min(4vw, 40px) 40px;
    }
    section {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
    }
    .panel { padding: 16px; }
    h2 { margin: 0 0 10px; font-size: 1rem; }
    label { display: block; margin: 12px 0 5px; color: var(--muted); font-size: .86rem; font-weight: 700; }
    input, select, textarea {
      width: 100%;
      border: 1px solid #bccabe;
      border-radius: 4px;
      padding: 10px;
      color: var(--ink);
      background: #fff;
      font: inherit;
    }
    textarea { min-height: 105px; resize: vertical; }
    .small { min-height: 76px; }
    .check { display: flex; gap: 8px; align-items: flex-start; margin-top: 12px; color: var(--ink); font-weight: 400; }
    .check input { width: auto; margin-top: 3px; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
    button {
      border: 0;
      border-radius: 4px;
      min-height: 42px;
      padding: 0 14px;
      color: #fff;
      background: var(--green);
      font-weight: 800;
      cursor: pointer;
    }
    button.secondary { color: var(--green-dark); background: var(--gold); }
    button.ghost { color: var(--green-dark); background: var(--green-soft); }
    button:disabled { cursor: wait; opacity: .7; }
    .output {
      min-height: 520px;
      padding: 18px;
      white-space: pre-wrap;
      background: #fff;
      font-family: Consolas, "Courier New", monospace;
      font-size: .94rem;
    }
    .status {
      margin-top: 12px;
      color: var(--muted);
      font-size: .9rem;
    }
    .warning { color: var(--danger); }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <strong>EPA RERC Grant Finder companion</strong>
    <h1>Grant-at-Arms</h1>
    <p>Draft grant language from a selected grant, local notes, basic public data, and reference files you keep on this computer.</p>
  </header>
  <main>
    <section class="panel">
      <h2>Project Inputs</h2>
      <label for="community">Community</label>
      <input id="community" placeholder="Example: Damascus">
      <label for="state">State</label>
      <select id="state"></select>
      <label for="projectTitle">Project title</label>
      <input id="projectTitle" placeholder="Example: Trailhead and downtown wayfinding">
      <label for="projectSummary">Project summary</label>
      <textarea id="projectSummary" class="small" placeholder="What do you want to build, plan, or improve?"></textarea>
      <label for="grantSelect">Public grant data</label>
      <select id="grantSelect"><option value="">Load grant data first</option></select>
      <div class="actions">
        <button id="loadGrants" class="ghost" type="button">Load public grants</button>
      </div>
      <label for="selectedGrant">Selected grant context</label>
      <textarea id="selectedGrant" placeholder="Paste selected grant details or load them from the public grant data."></textarea>
      <label for="matchCapacity">Match or local capacity</label>
      <textarea id="matchCapacity" class="small" placeholder="Local cash match, in-kind support, staff capacity, partners, or constraints."></textarea>
      <label for="sourceNotes">Source notes</label>
      <textarea id="sourceNotes" class="small" placeholder="Deadline, source URL, eligibility notes, and anything that must be verified."></textarea>
      <label for="fileInput">Read text files</label>
      <input id="fileInput" type="file" multiple accept=".txt,.md,.csv,.json">
      <label for="projectNotes">Project notes and file text</label>
      <textarea id="projectNotes" placeholder="Paste notes, or choose local text files above."></textarea>
      <label class="check"><input id="usePublicData" type="checkbox" checked> Pull a basic Census place profile when possible.</label>
    </section>
    <section class="panel">
      <h2>Drafting Engine</h2>
      <label for="provider">Provider</label>
      <select id="provider">
        <option value="ollama">Local Ollama</option>
        <option value="fallback">Structured fallback</option>
        <option value="api">OpenAI-compatible API</option>
      </select>
      <label for="model">Ollama model</label>
      <input id="model" value="gemma3:4b">
      <label for="apiEndpoint">API endpoint</label>
      <input id="apiEndpoint" value="https://api.openai.com/v1/chat/completions">
      <label for="apiModel">API model</label>
      <input id="apiModel" placeholder="Example: gpt-4.1-mini">
      <label for="apiKey">API key</label>
      <input id="apiKey" type="password" autocomplete="off" placeholder="Only used for this request. Not saved.">
      <div class="actions">
        <button id="draftButton" class="secondary" type="button">Draft narrative</button>
        <button id="downloadMd" class="ghost" type="button">Download Markdown</button>
        <button id="downloadDoc" class="ghost" type="button">Download Word Doc</button>
        <button id="copyDraft" class="ghost" type="button">Copy</button>
      </div>
      <p id="status" class="status">Ready.</p>
      <div id="output" class="output" aria-live="polite">Your draft will appear here.</div>
    </section>
  </main>
  <script>
    const states = ["","Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","District of Columbia","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"];
    const stateSelect = document.getElementById("state");
    states.forEach((state) => {
      const option = document.createElement("option");
      option.value = state;
      option.textContent = state || "Choose a state";
      stateSelect.appendChild(option);
    });

    let lastDraft = "";
    const status = document.getElementById("status");
    const output = document.getElementById("output");

    function setStatus(message, warning=false) {
      status.textContent = message;
      status.className = warning ? "status warning" : "status";
    }

    function collectPayload() {
      return {
        community: document.getElementById("community").value,
        state: document.getElementById("state").value,
        projectTitle: document.getElementById("projectTitle").value,
        projectSummary: document.getElementById("projectSummary").value,
        selectedGrant: document.getElementById("selectedGrant").value,
        matchCapacity: document.getElementById("matchCapacity").value,
        sourceNotes: document.getElementById("sourceNotes").value,
        projectNotes: document.getElementById("projectNotes").value,
        usePublicData: document.getElementById("usePublicData").checked,
        provider: document.getElementById("provider").value,
        model: document.getElementById("model").value,
        apiEndpoint: document.getElementById("apiEndpoint").value,
        apiModel: document.getElementById("apiModel").value,
        apiKey: document.getElementById("apiKey").value
      };
    }

    async function loadGrants() {
      setStatus("Loading public grant data...");
      const response = await fetch("/api/grants");
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      const grantSelect = document.getElementById("grantSelect");
      grantSelect.innerHTML = '<option value="">Choose a grant</option>';
      data.grants.forEach((grant, index) => {
        const option = document.createElement("option");
        option.value = index;
        option.textContent = `${grant.program || "Untitled"} - ${grant.agency || "Agency not listed"}`;
        option.dataset.grant = JSON.stringify(grant, null, 2);
        grantSelect.appendChild(option);
      });
      setStatus(`Loaded ${data.grants.length} public grant records.`);
    }

    document.getElementById("loadGrants").addEventListener("click", () => {
      loadGrants().catch((error) => setStatus(`Could not load grant data: ${error.message}`, true));
    });

    document.getElementById("grantSelect").addEventListener("change", (event) => {
      const option = event.target.selectedOptions[0];
      document.getElementById("selectedGrant").value = option?.dataset?.grant || "";
    });

    document.getElementById("fileInput").addEventListener("change", async (event) => {
      const notes = document.getElementById("projectNotes");
      const parts = [];
      for (const file of event.target.files) {
        const text = await file.text();
        parts.push(`\n--- Uploaded file: ${file.name} ---\n${text}`);
      }
      notes.value = `${notes.value}\n${parts.join("\n")}`.trim();
      setStatus(`Read ${event.target.files.length} file(s).`);
    });

    document.getElementById("draftButton").addEventListener("click", async () => {
      const button = document.getElementById("draftButton");
      button.disabled = true;
      setStatus("Drafting...");
      try {
        const response = await fetch("/api/draft", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(collectPayload())
        });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        lastDraft = data.draft;
        const warnings = data.warnings && data.warnings.length ? `\n\nWarnings:\n- ${data.warnings.join("\n- ")}` : "";
        output.textContent = `${data.draft}${warnings}`;
        setStatus(`Draft ready. Provider: ${data.provider}. Local knowledge read: ${data.localKnowledgeChars} characters.`);
      } catch (error) {
        setStatus(`Draft failed: ${error.message}`, true);
      } finally {
        button.disabled = false;
      }
    });

    function download(filename, text, type) {
      const blob = new Blob([text || output.textContent], {type});
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    }

    document.getElementById("downloadMd").addEventListener("click", () => download("grant-at-arms-draft.md", lastDraft, "text/markdown"));
    document.getElementById("downloadDoc").addEventListener("click", () => {
      const body = `<html><body><pre style="font-family: Arial, sans-serif; white-space: pre-wrap;">${lastDraft.replace(/[&<>]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}</pre></body></html>`;
      download("grant-at-arms-draft.doc", body, "application/msword");
    });
    document.getElementById("copyDraft").addEventListener("click", async () => {
      await navigator.clipboard.writeText(lastDraft || output.textContent);
      setStatus("Draft copied.");
    });
  </script>
</body>
</html>"""


class GrantAtArmsHandler(BaseHTTPRequestHandler):
    server_version = "GrantAtArms/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format % args))

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, body: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self.send_text(HTML_PAGE)
            return
        if self.path == "/health":
            self.send_json({"status": "ok", "app": "Grant-at-Arms"})
            return
        if self.path == "/api/grants":
            try:
                self.send_json(fetch_public_grants())
            except Exception as exc:
                self.send_json({"error": html.escape(str(exc))}, status=502)
            return
        self.send_text("Not found", status=404, content_type="text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/api/draft":
            self.send_text("Not found", status=404, content_type="text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.send_json(build_draft(payload))
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)


def serve(host: str, port: int) -> int:
    server = ThreadingHTTPServer((host, port), GrantAtArmsHandler)
    print(f"Grant-at-Arms is running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Grant-at-Arms.")
    finally:
        server.server_close()
    return 0


def smoke() -> int:
    sample = {
        "community": "Damascus",
        "state": "Virginia",
        "projectTitle": "Trailhead Wayfinding",
        "projectSummary": "Improve access from downtown to nearby trail assets.",
        "selectedGrant": "Sample grant record",
        "matchCapacity": "Limited local match",
        "sourceNotes": "Check current source before submission.",
        "usePublicData": False,
        "provider": "fallback",
    }
    result = build_draft(sample)
    assert "Draft Grant Narrative" in result["draft"]
    print(json.dumps({"status": "PASS", "model": DEFAULT_MODEL, "localKnowledgeChars": result["localKnowledgeChars"]}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant-at-Arms local grant writer")
    parser.add_argument("--serve", action="store_true", help="start the local web interface")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8789)
    parser.add_argument("--smoke", action="store_true", help="run a no-network smoke test")
    args = parser.parse_args()

    if args.smoke:
        return smoke()
    if args.serve:
        return serve(args.host, args.port)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
