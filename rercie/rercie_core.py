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
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


APP_VERSION = "0.3.4"
APP_DIR = Path(os.environ.get("RERCIE_APP_ROOT") or (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent))
ASSET_DIR = APP_DIR / "assets"
if not ASSET_DIR.is_dir() and not getattr(sys, "frozen", False):
    ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
LOCAL_KNOWLEDGE_DIR = APP_DIR / "local_knowledge"
PUBLIC_CATALOG_URL = "https://henkelpress.github.io/rerc-grant-finder/data.js"
CATALOG_PREFIXES = ("window.RERC_CATALOG = ", "window.GRANT_EXPLORER_DATA = ")
DEFAULT_MODEL = "gemma-3-1b-it-Q4_K_M.gguf"
LOCAL_CHAT_URL = os.environ.get("RERCIE_LOCAL_CHAT_URL", "http://127.0.0.1:8788/v1/chat/completions")
LOCAL_HEALTH_URL = os.environ.get("RERCIE_LOCAL_HEALTH_URL", "http://127.0.0.1:8788/health")
LOCAL_MODELS_URL = os.environ.get("RERCIE_LOCAL_MODELS_URL", "http://127.0.0.1:8788/v1/models")
SESSION_TOKEN = os.environ.get("RERCIE_SESSION_TOKEN", "")
EXPECTED_HOST = os.environ.get("RERCIE_EXPECTED_HOST", "127.0.0.1:8789").lower()
EXPECTED_ORIGIN = f"http://{EXPECTED_HOST}"
CENSUS_YEAR = "2024"
CENSUS_ISLAND_YEAR = "2020"
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

ISLAND_AREA_DATASETS = {
    "American Samoa": "dhcas",
    "Guam": "dhcgu",
    "Northern Mariana Islands": "dhcmp",
    "U.S. Virgin Islands": "dhcvi",
}

SYSTEM_PROMPT = """You are RERCie, a careful grant-writing assistant for rural communities.

Treat the supplied project text, funding record, verified public profile, and local reference files as the complete evidence boundary. A fact is supported only when it appears explicitly in that evidence. Do not use general knowledge to describe the community or funding program. Never create a number, date, amount, percentage, distance, timeline, study, survey, current condition, eligibility rule, partner, commitment, or budget allocation. Use proposed or intended language for future benefits. Write a document, not a conversation. Mark missing local facts as [add local fact] and unconfirmed funding rules as [check official source]. A person must review the draft before submission."""


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


def _local_env_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    env_path = Path.home() / ".env"
    try:
        for raw_line in env_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, candidate = line.split("=", 1)
            if key.strip() == name:
                return candidate.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _normalize_geography_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"\bst[.]?\b", "saint", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    suffixes = {
        "city", "town", "village", "borough", "municipality", "municipio", "cdp",
        "county", "parish", "census area", "city and borough",
    }
    for suffix in sorted(suffixes, key=len, reverse=True):
        if text.endswith(" " + suffix):
            text = text[: -(len(suffix) + 1)].strip()
            break
    return text


def _best_geography_record(rows: Any, community: str) -> dict[str, str]:
    if not isinstance(rows, list) or len(rows) < 2:
        return {}
    headers = rows[0]
    target = _normalize_geography_name((community or "").split(",", 1)[0])
    if not target:
        return {}
    scored: list[tuple[int, int, dict[str, str]]] = []
    for row in rows[1:]:
        record = dict(zip(headers, row, strict=False))
        candidate = _normalize_geography_name(record.get("NAME", "").split(",", 1)[0])
        if candidate == target:
            score = 4
        elif candidate.startswith(target + " ") or target.startswith(candidate + " "):
            score = 3
        elif target in candidate or candidate in target:
            score = 2
        else:
            continue
        scored.append((score, -abs(len(candidate) - len(target)), record))
    if not scored:
        return {}
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if len(scored) > 1 and scored[0][:2] == scored[1][:2]:
        return {}
    return scored[0][2]


def _census_url(path: str, params: dict[str, str]) -> str:
    return f"https://api.census.gov/data/{path}?{urllib.parse.urlencode(params)}"


def fetch_census_community_profile(community: str, state: str, census_api_key: str = "") -> dict[str, str]:
    community = (community or "").split(",", 1)[0].strip()
    state = (state or "").strip()
    fips = STATE_FIPS.get(state)
    if not community or not fips:
        return {}
    api_key = (census_api_key or _local_env_value("CENSUS_API_KEY")).strip()
    if not api_key:
        raise PermissionError("A free Census API key is needed for community facts. Open Community lookup help to add one.")

    if state in ISLAND_AREA_DATASETS:
        dataset = ISLAND_AREA_DATASETS[state]
        params = {"get": "NAME,P1_001N", "for": f"state:{fips}", "key": api_key}
        rows = request_json(_census_url(f"{CENSUS_ISLAND_YEAR}/dec/{dataset}", params), timeout=30)
        record = dict(zip(rows[0], rows[1], strict=False)) if isinstance(rows, list) and len(rows) > 1 else {}
        if not record:
            return {}
        return {
            "source": f"U.S. Census Bureau {CENSUS_ISLAND_YEAR} Island Areas Census",
            "source_url": "https://www.census.gov/data/developers/data-sets/decennial-census.html",
            "year": CENSUS_ISLAND_YEAR,
            "geography_type": "territory",
            "place": record.get("NAME", state),
            "population": record.get("P1_001N", ""),
            "coverage_note": f"Community-level ACS profiles are not available through this endpoint, so RERCie used territory-level context for {state}.",
        }

    fields = "NAME,DP05_0001E,DP03_0062E,DP03_0128PE,DP05_0018E"
    explicit_county = bool(re.search(r"\b(county|parish|census area)\b", community, re.IGNORECASE))
    geography_types = ("county", "place") if explicit_county else ("place", "county")
    for geography_type in geography_types:
        params = {"get": fields, "for": f"{geography_type}:*", "in": f"state:{fips}", "key": api_key}
        rows = request_json(_census_url(f"{CENSUS_YEAR}/acs/acs5/profile", params), timeout=30)
        record = _best_geography_record(rows, community)
        if not record:
            continue
        geoid = fips + record.get(geography_type, "")
        summary_level = "160" if geography_type == "place" else "050"
        return {
            "source": f"U.S. Census Bureau ACS {CENSUS_YEAR} 5-year profile",
            "source_url": f"https://data.census.gov/profile?g={summary_level}XX00US{geoid}",
            "year": CENSUS_YEAR,
            "geography_type": geography_type,
            "place": record.get("NAME", ""),
            "population": record.get("DP05_0001E", ""),
            "median_age": record.get("DP05_0018E", ""),
            "median_household_income": record.get("DP03_0062E", ""),
            "poverty_rate_percent": record.get("DP03_0128PE", ""),
        }
    return {}


def lookup_community_profile(community: str, state: str, census_api_key: str = "") -> dict[str, Any]:
    if not (community or "").strip() or not (state or "").strip():
        return {"profile": {}, "message": "Enter a community and choose a state or territory first.", "status": "missing_input"}
    try:
        profile = fetch_census_community_profile(community, state, census_api_key)
    except PermissionError as exc:
        return {"profile": {}, "message": str(exc), "status": "key_required"}
    except Exception:
        return {"profile": {}, "message": "Community facts could not be reached right now. The draft will mark local facts that still need to be added.", "status": "unavailable"}
    if not profile:
        return {"profile": {}, "message": "No exact Census place or county match was found. Check the community name or add local facts in the notes.", "status": "not_found"}
    return {"profile": profile, "message": f"Community facts found for {profile.get('place', community)}.", "status": "found"}

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


def format_public_profile(public_profile: dict[str, str]) -> str:
    if not public_profile:
        return "[No verified public community profile was found. Do not guess local statistics.]"
    lines = [
        f"Verified geography: {public_profile.get('place', '[not listed]')}",
        f"Geography type: {public_profile.get('geography_type', '[not listed]')}",
    ]
    population = str(public_profile.get("population") or "").strip()
    income = str(public_profile.get("median_household_income") or "").strip()
    median_age = str(public_profile.get("median_age") or "").strip()
    poverty = str(public_profile.get("poverty_rate_percent") or "").strip()
    if population.lstrip("-").isdigit():
        lines.append(f"Population: {int(population):,}")
    if median_age:
        lines.append(f"Median age: {median_age} years")
    if income.lstrip("-").isdigit():
        lines.append("Median household income: $" + f"{int(income):,}")
    if poverty:
        lines.append(f"People below the poverty line: {poverty}%")
    if public_profile.get("coverage_note"):
        lines.append(f"Coverage note: {public_profile['coverage_note']}")
    lines.append(f"Source: {public_profile.get('source', 'U.S. Census Bureau')}")
    if public_profile.get("source_url"):
        lines.append(f"Official profile: {public_profile['source_url']}")
    return "\n".join(f"- {line}" for line in lines)


def compose_prompt(payload: dict[str, Any], public_profile: dict[str, str], local_knowledge: str) -> str:
    profile_text = format_public_profile(public_profile)
    return f"""Write a useful first-draft grant narrative for a community team to edit.

Community: {payload.get('community') or '[add community]'}, {payload.get('state') or '[add state or territory]'}
Project title: {payload.get('projectTitle') or '[add project title]'}
Project summary: {payload.get('projectSummary') or '[add project summary]'}

Selected funding record:
{payload.get('selectedGrant') or '[select a funding source]'}

Match, staff, and partner capacity:
{payload.get('matchCapacity') or '[add match and capacity facts]'}

Verified public community context:
{profile_text}

Project notes and uploaded text:
{payload.get('projectNotes') or '[add project notes]'}

Facts to check on the official funding page:
{payload.get('sourceNotes') or '[add source notes]'}

Local reference files:
{local_knowledge or '[no local reference files loaded]'}

Write Markdown with these level-two sections in this order: Fit Summary; Project Need; Community Context; Proposed Work; Community Benefit; Work Plan; Budget and Match Notes; Source and Eligibility Checks; Missing Details.

Writing requirements:
- Write cohesive short paragraphs, not a template conversation or a list of generic claims.
- Use the verified public facts exactly and name their source in Community Context.
- Connect only the stated project actions and verified facts; do not invent local conditions, outcomes, eligibility, deadlines, award amounts, match rules, partners, budgets, or commitments.
- Do not repeat the same caution in every section.
- Put unknown local facts in Missing Details as [add local fact].
- Put each unconfirmed funding rule in Source and Eligibility Checks as [check official source].
- Make the draft specific enough that a community can improve it, while preserving uncertainty.
- Do not include any number unless that exact number appears in the supplied evidence above.
- Do not create a study, survey, traffic condition, economic effect, budget, match amount, timeline, required partner, or eligibility rule.
- When the evidence does not support a claim, omit it and add the missing item under Missing Details.
""".strip()


def call_local_writer(prompt: str, model: str) -> str:
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 0.9,
        "repeat_penalty": 1.08,
        "max_tokens": 2600,
        "stream": False,
    }
    data = request_json(LOCAL_CHAT_URL, payload=payload, timeout=300)
    choices = data.get("choices") or []
    return choices[0].get("message", {}).get("content", "").strip() if choices else ""


def _funding_record_text(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "[select a funding source]"
    try:
        record = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return raw[:5000]
    if not isinstance(record, dict):
        return raw[:5000]
    fields = (
        ("Program", record.get("title") or record.get("program")),
        ("Organization", record.get("organization") or record.get("agency")),
        ("Description", record.get("description")),
        ("Best for", record.get("best_for") or record.get("bestFor")),
        ("Official page", record.get("url") or record.get("source_url")),
    )
    return "\n".join(f"- {label}: {value}" for label, value in fields if value) or raw[:5000]


def _as_sentence(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else text + "."


def deterministic_scaffold(payload: dict[str, Any], public_profile: dict[str, str]) -> str:
    community = str(payload.get("community") or "[add community]").strip()
    state = str(payload.get("state") or "[add state or territory]").strip()
    title = str(payload.get("projectTitle") or "[add project title]").strip()
    summary = _as_sentence(str(payload.get("projectSummary") or "[add project summary]"))
    project_notes = str(payload.get("projectNotes") or "").strip()[:1800]
    grant = _funding_record_text(payload.get("selectedGrant"))
    match = str(payload.get("matchCapacity") or "[add match, staff, and partner capacity facts]").strip()
    source = str(payload.get("sourceNotes") or "[add the official source link and current funding details]").strip()
    profile = format_public_profile(public_profile)
    notes_block = (
        f"\n\nProject notes supplied by the community:\n\n{project_notes}"
        if project_notes
        else "\n\n[add local fact] Add confirmed project tasks, locations, partners, and expected results."
    )
    return f"""# {title}

## Fit Summary

{community}, {state}, is considering the {title} project. The community describes the project as follows: {summary}

The funding record supplied below may be worth screening for this project. [check official source] Confirm that the applicant, location, proposed work, costs, schedule, and attachments meet the current rules.

{grant}

## Project Need

The community has identified the following need: {summary}

Use the final application to explain the size and effect of this need with checked local evidence. [add local fact]

## Community Context

{profile}

## Proposed Work

The current concept is based on the project summary and the community-supplied notes below.{notes_block}

Before submission, turn this concept into a confirmed scope with clear tasks, locations, responsible parties, approvals, deliverables, and measures of success.

## Community Benefit

If completed as described, {title} is intended to help {community} advance the purpose stated in the project summary. The final application should identify who would benefit, explain how they would benefit, and support those statements with local plans, records, or partner documentation. [add local fact]

## Work Plan

1. Confirm the project scope, location, applicant, and responsible staff.
2. Check the funding program's current eligibility and application requirements.
3. Define the tasks, approvals, partners, deliverables, and measures that apply to this project.
4. Build a supported budget, schedule, and match plan.
5. Complete the application and establish a practical method for tracking results.

## Budget and Match Notes

{match}

[check official source] Confirm allowed costs, award limits, match rules, and required budget documentation before finalizing the budget.

## Source and Eligibility Checks

Community notes about the official source:

{source}

- [check official source] Confirm eligible applicants, locations, activities, and costs.
- [check official source] Confirm the current deadline, award range, match, and required attachments.

## Missing Details

- [add local fact] Applicant legal name and confirmed project location.
- [add local fact] Checked evidence showing the need and people served.
- [add local fact] Confirmed scope, schedule, staff, partners, and expected results.
- [add local fact] Total budget and committed match.
- [check official source] Current funding rules and application instructions.
"""


_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16",
    "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20",
}


def _number_tokens(text: str) -> set[str]:
    tokens = set()
    for raw in re.findall(r"(?<![A-Za-z0-9])[$]?(\d[\d,]*(?:\.\d+)?)%?", text or ""):
        normalized = raw.replace(",", "").lstrip("0") or "0"
        tokens.add(normalized)
    lowered = (text or "").lower()
    for word, number in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", lowered):
            tokens.add(number)
    return tokens


def _word_tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text or "")}


def grounding_issues(draft: str, payload: dict[str, Any], public_profile: dict[str, str]) -> list[str]:
    evidence_parts = [
        str(payload.get("community") or ""), str(payload.get("state") or ""),
        str(payload.get("projectTitle") or ""), str(payload.get("projectSummary") or ""),
        str(payload.get("selectedGrant") or ""), str(payload.get("matchCapacity") or ""),
        str(payload.get("sourceNotes") or ""), str(payload.get("projectNotes") or ""),
        json.dumps(public_profile, ensure_ascii=True),
    ]
    evidence = "\n".join(evidence_parts)
    evidence_lower = evidence.lower()
    allowed_numbers = _number_tokens(evidence)
    draft_without_list_numbers = re.sub(r"(?m)^\s*\d+[.)]\s+", "", draft or "")
    unexpected_numbers = sorted(_number_tokens(draft_without_list_numbers) - allowed_numbers)
    issues = [f"unsupported number: {number}" for number in unexpected_numbers]
    safe_scaffold = deterministic_scaffold(payload, public_profile)
    if re.sub(r"\s+", " ", draft or "").strip() != re.sub(r"\s+", " ", safe_scaffold).strip():
        allowed_words = _word_tokens(safe_scaffold)
        novel_words = sorted(_word_tokens(draft or "") - allowed_words)
        if novel_words:
            issues.append("unsupported wording: " + ", ".join(novel_words[:12]))
        suspicious_patterns = (
            r"\b(?:study|survey|poll)\b",
            r"\b(?:currently|existing|recent growth|has experienced|have experienced)\b",
            r"\b(?:traffic|congestion|accident|revenue)\b",
            r"\b(?:ada standards?|request for proposals?|rfp)\b",
            r"\b(?:department|commission|planning and zoning|town council)\b",
            r"\b(?:maple street|main street|historic district)\b",
            r"\b(?:acquir\w*|purchas\w*|consult\w*|hir\w*|contract\w*|approval\w*|permit\w*)\b",
            r"\b(?:community|resident|public) support\b",
            r"\b(?:has|have|will) (?:secured|committed|approved|funded)\b",
        )
        for pattern in suspicious_patterns:
            for match in re.finditer(pattern, draft or "", re.IGNORECASE):
                phrase = match.group(0).lower()
                if phrase not in evidence_lower:
                    issues.append(f"unsupported detail: {phrase}")
    return sorted(set(issues))

def build_draft(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("usePublicData"):
        profile_lookup = lookup_community_profile(
            str(payload.get("community") or ""),
            str(payload.get("state") or ""),
            str(payload.get("censusApiKey") or ""),
        )
    else:
        profile_lookup = {"profile": {}, "message": "Community lookup was turned off.", "status": "skipped"}
    public_profile = profile_lookup["profile"]
    provider = str(payload.get("provider") or "local").lower()
    if provider not in {"local", "fallback"}:
        provider = "local"
    local_knowledge = load_local_knowledge()
    prompt = compose_prompt(payload, public_profile, local_knowledge)
    model = DEFAULT_MODEL
    warnings: list[str] = []
    try:
        draft = call_local_writer(prompt, model) if provider == "local" else deterministic_scaffold(payload, public_profile)
    except Exception:
        warnings.append("The local Gemma writer could not finish, so RERCie made a fill-in outline instead.")
        draft = deterministic_scaffold(payload, public_profile)
    if not draft.strip():
        warnings.append("RERCie could not make a full draft, so it made a fill-in outline instead.")
        draft = deterministic_scaffold(payload, public_profile)
    return {
        "draft": draft, "provider": provider, "model": model, "publicProfile": public_profile,
        "profileMessage": profile_lookup["message"], "profileStatus": profile_lookup["status"],
        "localKnowledgeChars": len(local_knowledge), "warnings": warnings, "safetyNotice": "",
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
    .lookup-help { margin-top:10px; padding:10px 12px; border:1px solid var(--line); background:#fafcfb; }
    .lookup-help summary { color:var(--forest); font-weight:800; cursor:pointer; }
    .community-profile { margin-top:10px; padding:12px; border-left:5px solid var(--river); background:var(--sky); }
    .community-profile strong { display:block; margin-bottom:4px; }
    .community-profile ul { margin:6px 0; padding-left:20px; }
    .working { margin:12px 0; padding:12px; border:1px solid #b8d6c5; background:#eef7f1; }
    .working-row { display:flex; justify-content:space-between; gap:12px; color:var(--forest); font-weight:800; }
    .working progress { display:block; width:100%; height:14px; margin-top:8px; accent-color:var(--green); }
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
  <div class="privacy"><strong>Private by default:</strong> Gemma writing and local reference files stay on this computer. Census and catalog lookups use public websites.</div>
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
      <label class="check" for="usePublicData"><input id="usePublicData" type="checkbox" checked><span>Look for public community facts from the U.S. Census Bureau.</span></label>
      <div class="actions"><button id="lookupCommunity" class="quiet" type="button">Look up community facts</button></div>
      <details class="lookup-help"><summary>Community lookup help</summary><p class="section-note">The Census Bureau now requires a free API key. RERCie will use <code>CENSUS_API_KEY</code> from this computer when available, or you can paste a key below for this session.</p><label for="censusApiKey">Census API key</label><input id="censusApiKey" type="password" autocomplete="off" placeholder="Optional on a computer that already has a Census key"><p class="section-note"><a href="https://api.census.gov/data/key_signup.html" target="_blank" rel="noopener">Get a free Census API key</a></p></details>
      <div id="communityProfile" class="community-profile" hidden aria-live="polite"></div>
    </section>
    <section class="panel">
      <div class="engine">
        <div><label for="provider">Writing method</label><select id="provider"><option value="local">Local Gemma writer</option><option value="fallback">Structured outline only</option></select></div>
        <span id="runtime" class="runtime">Checking local writer...</span>
      </div>
      <div class="actions">
        <button id="draftButton" class="secondary" type="button">Create first draft</button>
        <button id="downloadDocx" class="quiet" type="button">Export Word</button>
        <button id="downloadMd" class="quiet" type="button">Export Markdown</button>
        <button id="copyDraft" class="quiet" type="button">Copy</button>
      </div>
      <div id="working" class="working" hidden aria-live="polite">
        <div class="working-row"><span id="workingLabel">RERCie is working...</span><span id="workingTime">0 seconds</span></div>
        <progress aria-label="RERCie is generating the draft"></progress>
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
    let workingTimer=0;
    function startWorking(){ const box=document.getElementById("working"); const label=document.getElementById("workingLabel"); const clock=document.getElementById("workingTime"); const started=Date.now(); box.hidden=false; label.textContent="RERCie is generating a draft with local Gemma..."; const tick=()=>{ const elapsed=Math.floor((Date.now()-started)/1000); clock.textContent=elapsed+" seconds"; }; tick(); workingTimer=window.setInterval(tick,1000); }
    function stopWorking(){ document.getElementById("working").hidden=true; if(workingTimer){window.clearInterval(workingTimer);workingTimer=0;} }
    function formatProfileValue(key,value){ if((key==="population"||key==="median_household_income")&&/^\d+$/.test(String(value))){ const number=Number(value).toLocaleString(); return key==="median_household_income"?"$"+number:number; } return String(value); }
    function renderProfile(profile,message,lookupStatus){ const box=document.getElementById("communityProfile"); box.replaceChildren(); box.hidden=false; const heading=document.createElement("strong"); heading.textContent=profile&&profile.place?profile.place:"Community facts"; box.appendChild(heading); if(!profile||!Object.keys(profile).length){ const note=document.createElement("span"); note.textContent=message||"No community facts were found."; box.appendChild(note); if(lookupStatus==="key_required"){document.querySelector(".lookup-help").open=true;} return; } const labels={population:"Population",median_age:"Median age",median_household_income:"Median household income",poverty_rate_percent:"People below the poverty line",geography_type:"Geography used"}; const list=document.createElement("ul"); Object.keys(labels).forEach((key)=>{ if(!profile[key])return; const item=document.createElement("li"); let value=formatProfileValue(key,profile[key]); if(key==="median_age")value+=" years"; if(key==="poverty_rate_percent")value+="%"; item.textContent=labels[key]+": "+value; list.appendChild(item); }); box.appendChild(list); const source=document.createElement(profile.source_url?"a":"span"); source.textContent=profile.source||"U.S. Census Bureau"; if(profile.source_url){source.href=profile.source_url;source.target="_blank";source.rel="noopener";} box.appendChild(source); if(profile.coverage_note){ const coverage=document.createElement("p"); coverage.textContent=profile.coverage_note; box.appendChild(coverage); } }
    async function lookupCommunityFacts(){ const button=document.getElementById("lookupCommunity"); button.disabled=true; setStatus("Looking up community facts..."); try{ const body={community:document.getElementById("community").value,state:stateSelect.value,censusApiKey:document.getElementById("censusApiKey").value}; const response=await apiFetch("/api/community-profile",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}); const data=await response.json(); if(!response.ok)throw new Error(data.error||"Lookup failed."); renderProfile(data.profile,data.message,data.status); setStatus(data.message,data.status!=="found"); }catch(error){renderProfile({},"Community facts could not be reached right now.","unavailable");setStatus("Community lookup failed: "+error.message,true);}finally{button.disabled=false;} }
    function collectPayload(){ return {community:document.getElementById("community").value,state:stateSelect.value,projectTitle:document.getElementById("projectTitle").value,projectSummary:document.getElementById("projectSummary").value,selectedGrant:document.getElementById("selectedGrant").value,matchCapacity:document.getElementById("matchCapacity").value,sourceNotes:document.getElementById("sourceNotes").value,projectNotes:document.getElementById("projectNotes").value,usePublicData:document.getElementById("usePublicData").checked,provider:document.getElementById("provider").value,model:"gemma-3-1b-it-Q4_K_M.gguf",censusApiKey:document.getElementById("censusApiKey").value}; }
    async function checkRuntime(){ const badge=document.getElementById("runtime"); try{ const response=await apiFetch("/api/runtime"); const data=await response.json(); badge.textContent=data.ready?"Local model ready":"Local model is starting"; badge.className=data.ready?"runtime":"runtime offline"; }catch{ badge.textContent="Could not check local writer"; badge.className="runtime offline"; } }
    async function loadGrants(){ setStatus("Loading the public funding list..."); const response=await apiFetch("/api/grants"); if(!response.ok) throw new Error((await response.json()).error||"The list could not be loaded."); const data=await response.json(); const select=document.getElementById("grantSelect"); select.innerHTML='<option value="">Choose a funding match</option>'; data.grants.forEach((grant,index)=>{ const option=document.createElement("option"); option.value=String(index); option.textContent=`${grant.title||grant.program||"Untitled"} - ${grant.organization||grant.agency||"Organization not listed"}`; option.dataset.grant=JSON.stringify(grant,null,2); select.appendChild(option); }); setStatus(`Loaded ${data.grants.length} funding options. Updated ${data.updated||"date not listed"}.`); }
    document.getElementById("loadGrants").addEventListener("click",()=>loadGrants().catch((error)=>setStatus(`Could not load funding: ${error.message}`,true)));
    document.getElementById("grantSelect").addEventListener("change",(event)=>{ document.getElementById("selectedGrant").value=event.target.selectedOptions[0]?.dataset?.grant||""; });
    document.getElementById("fileInput").addEventListener("change",async(event)=>{ const parts=[]; for(const file of event.target.files){ if(file.size>2000000){ setStatus(`${file.name} is too large. Use a text file under 2 MB.`,true); continue; } parts.push(`\n--- File: ${file.name} ---\n${await file.text()}`); } const notes=document.getElementById("projectNotes"); notes.value=`${notes.value}\n${parts.join("\n")}`.trim(); if(parts.length) setStatus(`Read ${parts.length} file(s).`); });
    document.getElementById("lookupCommunity").addEventListener("click",lookupCommunityFacts);
    document.getElementById("draftButton").addEventListener("click",async()=>{ const button=document.getElementById("draftButton"); button.disabled=true; startWorking(); setStatus("RERCie is preparing the draft..."); try{ const response=await apiFetch("/api/draft",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(collectPayload())}); const data=await response.json(); if(!response.ok) throw new Error(data.error||"Draft failed."); lastDraft=data.draft; output.textContent=data.draft; renderProfile(data.publicProfile,data.profileMessage,data.profileStatus); const readyMessage=data.localKnowledgeChars?"Draft ready. Local reference files were used.":"Draft ready."; setStatus(data.warnings?.length?data.warnings.join(" "):readyMessage+" "+(data.safetyNotice||"")+" "+(data.profileMessage||""),Boolean(data.warnings?.length)); }catch(error){ setStatus("Draft failed: "+error.message,true); }finally{ stopWorking(); button.disabled=false; } });
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
            if self.path == "/api/community-profile":
                self.send_json(lookup_community_profile(
                    str(payload.get("community") or ""),
                    str(payload.get("state") or ""),
                    str(payload.get("censusApiKey") or ""),
                ))
            elif self.path == "/api/draft":
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
    sample_rows = [
        ["NAME", "state", "place"],
        ["St. Paul town, Virginia", "51", "71616"],
        ["Damascus town, Virginia", "51", "21000"],
    ]
    assert _best_geography_record(sample_rows, "St Paul").get("place") == "71616"
    sample_profile = {"place": "St. Paul town, Virginia", "population": "1046", "median_household_income": "29554", "source": "Test source"}
    profile_text = format_public_profile(sample_profile)
    assert "Population: 1,046" in profile_text and "Median household income: $29,554" in profile_text
    assert "CENSUS_KEY_SENTINEL" not in compose_prompt({"projectTitle": "Test"}, sample_profile, "")
    unsafe_draft = "A survey found 70% support and an $85,000 budget."
    assert grounding_issues(unsafe_draft, {"projectSummary": "Improve a trail."}, sample_profile)
    unsafe_qualitative = "The town will acquire land, hire a consultant, obtain approvals, and has strong community support."
    assert grounding_issues(unsafe_qualitative, {"projectSummary": "Improve a trail."}, sample_profile)
    safe_scaffold = deterministic_scaffold({"community": "Test", "state": "Virginia", "projectTitle": "Trail", "projectSummary": "Improve a trail."}, sample_profile)
    assert not grounding_issues(safe_scaffold, {"community": "Test", "state": "Virginia", "projectTitle": "Trail", "projectSummary": "Improve a trail."}, sample_profile)
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
