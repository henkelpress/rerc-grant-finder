from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


PROGRAMS = {
    "Recreation Economy for Rural Communities",
    "Local Foods, Local Places",
    "EPA Brownfields Success Stories",
    "EPA Examples of Smart Growth Communities and Projects",
    "U.S. Climate Resilience Toolkit",
    "USDA Rural Development Success Stories",
}

SOURCE_TYPES = {
    "epa_rerc_partner_page",
    "epa_lflp_summary_report_pdf",
    "epa_brownfields_success_story_html",
    "epa_brownfields_success_story_pdf",
    "epa_smart_growth_example_detail_page",
    "us_climate_resilience_toolkit_case_page",
    "usda_rd_success_story_browser_seed",
}

PUBLIC_HOSTS = {
    "www.epa.gov",
    "epa.gov",
    "toolkit.climate.gov",
    "www.rd.usda.gov",
    "rd.usda.gov",
}

PLACE_OVERRIDES = {
    "Relocating the Native Village of Shishmaref, Alaska Due to Coastal Erosion": "Shishmaref",
    "Recertifying Utility Workers in a Small, Remote Community": "Multiple communities",
    "Adapting to Rising Tides in San Francisco Bay, California": "San Francisco Bay Area",
    "California State Coastal Conservancy: Gravel Beach and Berm for Shorebird Habitat Creation, Erosion Control and Flood Protection": "San Francisco Bay shoreline",
    "Lakewood, CO: Housing and the Arts at Lamar Street Station": "Lakewood",
    "Coastal Adaptation Plan for the Town of Groton, Connecticut": "Groton",
    "Brownfield to Brewery: DNREC delivers a win-win in Delaware": "Multiple communities",
    "Climate Change and the Florida Keys": "Florida Keys",
    "Climate Change in Port Heiden, AK": "Port Heiden",
    "Florida's Community Resiliency Initiative": "Multiple communities",
    "Oglethorpe Power's Acquisition of Walton County Power Strengthens Reliability and Affordability in Rural Georgia": "Monroe and rural Georgia",
    "Ferrous Site, Lawrence, Mass.": "Lawrence",
    "Shubuta, MS: Strengthening Shubuta": "Shubuta",
    "Ralls County Electric's Vision for a Stronger, Smarter Grid": "Ralls County service area",
    "CR4HC Case Study: University of Nebraska": "Omaha",
    "Planning for Climate Resilience-City of Asheville, North Carolina": "Asheville",
    "Minnkota Power Cooperative's $60 Million Infrastructure Upgrade for a Stronger Future": "Eastern North Dakota and northwestern Minnesota",
    "A Successful Transformation: Allentown Waterfront - Allentown, PA": "Allentown",
    "Former Alcoa Research Park New Kensington, PA": "New Kensington",
    "Homewood Senior Housing & Caf\u00e9 Homewood Ave, Pittsburgh, PA.": "Pittsburgh",
    "Pittsburgh, PA: Luxury Living with an Industrial Legacy": "Pittsburgh",
    "Brownfields Success Story: Common Success at Cooper Commons LLC": "Multiple communities",
    "Overbrook Environmental Education Center Becomes Community Hub: Philadelphia, PA": "Philadelphia",
    "Finding Solutions Through Distance Learning Technology": "Chamberlain and rural school communities",
    "Spearfish, SD Climate Resiliency Plan": "Spearfish",
    "Training a Workforce to Bring Nature-based Solutions into Every Project": "Puerto Rico and U.S. Virgin Islands",
    "City Market - South End (Onion River Co-op), Burlington, Vt.": "Burlington",
    "Vermont Climate Action Plan": "Multiple communities",
    "Promoting Ecotourism to Conserve a Watershed in Virginia": "Lower Chickahominy watershed",
    "The Edge of Something Special: Williamsburg, VA": "Williamsburg",
    "Seattle, WA: Redevelopment Yields Much-Needed Affordable Housing": "Seattle",
    "A Successful Transformation: The Adamston Commons": "Clarksburg",
    "Wellsburg, WV: A Local Manufacturing Expansion Takes Flight": "Wellsburg",
    "Beech Bottom, WV: Forging a New Future in Steel Country": "Beech Bottom",
    "Ranson and Charles Town, WV: A Tale of Two Cities": "Ranson and Charles Town",
    "A Successful Transformation: From Wasted Lot to Reading Hot\u2010Spot": "Shepherdstown",
}

PLACE_TYPE_OVERRIDES = {
    "Climate Change in Port Heiden, AK": "tribal_community",
    "Addressing Links Between Climate and Public Health in Alaska Native Villages": "tribal_community",
    "Alaska Native Villages Work to Enhance Local Economies as They Minimize Environmental Risks": "tribal_community",
    "Assessing the Timing and Extent of Coastal Change in Western Alaska": "tribal_community",
    "I\u00f1upiat Work to Preserve Food and Traditions on Alaska's North Slope": "tribal_community",
    "Lapwai, Idaho Local Foods, Local Places Summary Report": "tribal_community",
    "Mission, South Dakota Local Foods, Local Places Summary Report": "tribal_community",
    "Relocating the Native Village of Shishmaref, Alaska Due to Coastal Erosion": "tribal_community",
    "Recertifying Utility Workers in a Small, Remote Community": "statewide_or_multi_community",
    "Brownfield to Brewery: DNREC delivers a win-win in Delaware": "statewide_or_multi_community",
    "Florida's Community Resiliency Initiative": "statewide_or_multi_community",
    "Vermont Climate Action Plan": "statewide_or_multi_community",
    "Brownfields Success Story: Common Success at Cooper Commons LLC": "statewide_or_multi_community",
    "Adapting to Rising Tides in San Francisco Bay, California": "county_or_region",
    "California State Coastal Conservancy: Gravel Beach and Berm for Shorebird Habitat Creation, Erosion Control and Flood Protection": "county_or_region",
    "Climate Change and the Florida Keys": "county_or_region",
    "Oglethorpe Power's Acquisition of Walton County Power Strengthens Reliability and Affordability in Rural Georgia": "county_or_region",
    "Ralls County Electric's Vision for a Stronger, Smarter Grid": "county_or_region",
    "Minnkota Power Cooperative's $60 Million Infrastructure Upgrade for a Stronger Future": "county_or_region",
    "Finding Solutions Through Distance Learning Technology": "county_or_region",
    "Training a Workforce to Bring Nature-based Solutions into Every Project": "county_or_region",
    "Promoting Ecotourism to Conserve a Watershed in Virginia": "county_or_region",
}
INTERNAL_MARKERS = (
    "protos treats",
    "protos indexes",
    "record remains flagged",
    "image rights",
    "internal source",
    "local source",
)


def compact(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def repair_text(value: object) -> str:
    text = compact(value).replace("\u00a0", " ")
    markers = ("Ã", "Â", "â", "Æ", "ï¿½", "\ufffd")
    for _ in range(3):
        current_score = sum(text.count(marker) for marker in markers)
        if not current_score:
            break
        candidates = [text]
        for encoding in ("cp1252", "latin-1"):
            try:
                candidates.append(text.encode(encoding).decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                try:
                    candidates.append(text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore"))
                except (LookupError, UnicodeError):
                    pass
        best = min(candidates, key=lambda item: sum(item.count(marker) for marker in markers))
        if best == text:
            break
        text = best
    return text.strip()


def valid_place(value: str, title: str) -> bool:
    lowered = value.lower()
    if not value or len(value) > 72 or ":" in value:
        return False
    if any(token in lowered for token in (
        "$", "combined value", "grant recipient", "grant type", "authority", "commission",
        "district", "department", "agency", "foundation", "partnership", " inc", "company",
        "industrial development", "climate action plan", "successful transformation", "workers in",
        "planning for", "brownfield to", "site description",
    )):
        return False
    title_words = set(re.findall(r"[a-z]{4,}", title.lower()))
    place_words = set(re.findall(r"[a-z]{4,}", lowered))
    return not (len(place_words) >= 5 and len(place_words - title_words) <= 1)
def place_from_title(title: str) -> str:
    parts = [part.strip(" .") for part in title.split(",") if part.strip(" .")]
    if len(parts) < 2:
        return ""
    candidate = parts[-2]
    if ":" in candidate:
        candidate = candidate.rsplit(":", 1)[-1].strip()
    if not candidate or len(candidate) > 55:
        return ""
    return candidate


def clean_theme(value: object) -> str:
    theme = repair_text(value)
    lowered = theme.lower()
    if len(theme) > 48:
        return ""
    if any(marker in lowered for marker in ("complete evaluation", "funded through", "recipient", "contamination")):
        return ""
    return theme


def clean_summary(candidate: str) -> str:
    return repair_text(candidate)


def summary_is_public_ready(candidate: str, title: str) -> bool:
    lowered = candidate.lower()
    if len(candidate) < 55 or len(candidate) > 560:
        return False
    if any(marker in candidate for marker in ("Ã", "Â", "â", "Æ", "ï¿½", "\ufffd")):
        return False
    if any(marker in lowered for marker in ("epa grant recipients", "epa grant types", "site description", "site descrip", "photo courtesy", "image lessons learned", "figure 1", "years awarded", "grant types:", "grants and resources:")):
        return False
    if candidate[:1].islower() or "\u019f" in candidate:
        return False
    title_norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    candidate_norm = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
    repeated = f"{title_norm} is a climate resilience toolkit case record for {title_norm}"
    return candidate_norm != repeated


def fallback_summary(title: str, program: str, place: str, state: str, themes: list[str], year: str) -> str:
    location = state if place == "Multiple communities" else f"{place}, {state}"
    topic_text = ", ".join(theme.lower() for theme in themes[:3] if theme) or "community priorities"
    when = f"In {year}, " if year else ""
    if program == "Recreation Economy for Rural Communities":
        return f"{when}{location} received EPA planning assistance to connect outdoor recreation with {topic_text}. The official RERC page identifies the partner community and its planning focus."
    if program == "Local Foods, Local Places":
        return f"{when}{location} used Local Foods, Local Places planning assistance to work on {topic_text}. The official summary report records the community's goals and action steps."
    if program == "EPA Brownfields Success Stories":
        return f"This EPA success story describes how {location} addressed {title.lower()} and related land-reuse work. The official page provides the cleanup, partners, and results."
    if program == "EPA Examples of Smart Growth Communities and Projects":
        return f"This EPA example describes {title.lower()} in {location}, with lessons related to {topic_text}."
    if program == "U.S. Climate Resilience Toolkit":
        return f"This federal case study describes {title.lower()} in {location}, with lessons related to {topic_text}."
    return f"This USDA Rural Development story describes {title.lower()} in {location}, with details about {topic_text}."
def public_url(value: object) -> str:
    url = compact(value)
    if not url.startswith(("https://", "http://")):
        return ""
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return url if host.lower() in PUBLIC_HOSTS else ""


def sentence_summary(value: object, max_chars: int = 500) -> str:
    text = clean_summary(repair_text(value))
    if not text:
        return ""
    artifacts = (
        "photo credit", "photo courtesy", "pictured here", "download success story",
        "epa grant recipient", "epa grant type", "current use:", "former use",
        "supporting environmental excellence", "apply for local foods", "image lessons learned",
        "figure 1", "years awarded", "site descrip", "grant types:", "grants and resources:",
    )
    selected: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence = sentence.strip(" -")
        lowered = sentence.lower()
        if len(sentence) < 35 or len(sentence) > 300 or len(sentence.split()) > 42:
            continue
        if any(marker in lowered for marker in artifacts):
            continue
        if re.search(r"\b(?:protos|record remains|image rights|source manifest)\b", lowered):
            continue
        if re.search(r"\b(?:the|a|an|of|for|with|from|to|and|or|u\.s)\.?$", lowered):
            continue
        candidate = " ".join(selected + [sentence])
        if len(candidate) > max_chars:
            break
        selected.append(sentence)
        if len(selected) >= 2:
            break
    result = " ".join(selected)
    if result and result[-1] not in ".!?":
        result += "."
    return result


def public_case_prefix(case: dict) -> str:
    long_summary = repair_text((case.get("summary") or {}).get("long"))
    if not long_summary:
        return ""
    lowered = long_summary.lower()
    cut_points = [lowered.find(marker) for marker in INTERNAL_MARKERS if lowered.find(marker) >= 0]
    if cut_points:
        long_summary = long_summary[: min(cut_points)]
    return long_summary.strip()


def first_public_narrative(source: dict, case: dict) -> str:
    source_candidates: list[str] = []
    for unit in source.get("extracted_units", []):
        fields = unit.get("fields") or {}
        source_candidates.extend(
            repair_text(fields.get(key))
            for key in ("source_text", "summary", "description", "project_description")
        )
        source_candidates.append(repair_text(unit.get("text")))
    case_candidates = [
        public_case_prefix(case),
        *(repair_text(item.get("text")) for item in case.get("takeaways", [])),
        repair_text((case.get("summary") or {}).get("short")),
    ]
    if source.get("source_type") in {"epa_lflp_summary_report_pdf", "epa_rerc_partner_page"}:
        candidates = [case_candidates[-1], *case_candidates[:-1], *source_candidates]
    else:
        candidates = [*source_candidates, *case_candidates]
    for candidate in candidates:
        lowered = candidate.lower()
        if any(marker in lowered for marker in INTERNAL_MARKERS):
            continue
        summary = sentence_summary(candidate)
        if summary:
            return summary
    return ""

def year_for(case: dict, program_name: str) -> str:
    lookup = (case.get("geography") or {}).get("lookup_context") or {}
    values = [
        compact(lookup.get("year")),
        compact(lookup.get("year_published")),
    ]
    if program_name not in {"EPA Examples of Smart Growth Communities and Projects"}:
        values.append(compact((case.get("programs") or [{}])[0].get("project_or_round")))
    for value in values:
        match = re.search(r"\b(19|20)\d{2}\b", value)
        if match:
            return match.group(0)
    return ""

def stage_for(case: dict, program_name: str, source_url: str) -> str:
    if program_name == "EPA Brownfields Success Stories":
        return "Cleanup"
    if program_name in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"}:
        return "Planning"
    if program_name in {"EPA Examples of Smart Growth Communities and Projects", "USDA Rural Development Success Stories"}:
        return "Implementation"
    if "action-plan" in source_url or "action plan" in repair_text(case.get("title")).lower():
        return "Planning"
    return "Implementation"


def normalized_place_type(case: dict, place: str, state: str) -> str:
    title = repair_text(case.get("title"))
    if title in PLACE_TYPE_OVERRIDES:
        return PLACE_TYPE_OVERRIDES[title]
    geography = case.get("geography") or {}
    raw = repair_text(geography.get("place_type"))
    context = " ".join(
        [
            title,
            place,
            repair_text(case.get("case_type")),
            " ".join(repair_text(item) for item in case.get("themes", [])),
        ]
    ).lower()
    if re.search(r"\b(tribal|tribe|native village|reservation|pueblo|navajo|hopi|passamaquoddy)\b", context):
        return "tribal_community"
    if place == "Multiple communities":
        return "statewide_or_multi_community"
    if re.search(r"\b(county|region|regional|service area|watershed|bay area|shoreline|florida keys)\b", raw.lower() + " " + place.lower()):
        return "county_or_region"
    return "town_or_city"
def build_record(case_path: Path, checked_on: str) -> dict | None:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    program = (case.get("programs") or [{}])[0]
    program_name = compact(program.get("program_name"))
    if program_name not in PROGRAMS:
        return None

    geography = case.get("geography") or {}
    state = repair_text(geography.get("state"))
    title = repair_text(case.get("title"))
    place = PLACE_OVERRIDES.get(title, repair_text(geography.get("place_name")))
    if title not in PLACE_OVERRIDES and (place.lower() == state.lower() or not valid_place(place, title)):
        place = place_from_title(title) or "Multiple communities"
    if not state or state == "Unknown" or not place:
        return None
    if int((case.get("qaqc") or {}).get("blocker_count", 0) or 0):
        return None

    manifest_path = case_path.parent / compact(case.get("source_manifest"))
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = next(
        (
            item
            for item in manifest.get("sources", [])
            if item.get("source_type") in SOURCE_TYPES
            and item.get("review_status") not in {"blocked", "not_started"}
            and public_url(item.get("origin_path_or_url"))
        ),
        None,
    )
    if not source:
        return None

    summary = first_public_narrative(source, case)
    themes = [
        clean_theme(theme)
        for theme in case.get("themes", [])
        if clean_theme(theme)
        and clean_theme(theme).lower()
        not in {
            "rerc",
            "rural development",
            "case study",
            program_name.lower(),
            "epa success story",
            state.lower(),
        }
    ]
    themes = list(dict.fromkeys(themes))[:8]
    if not themes:
        fallback_theme = clean_theme(case.get("case_type"))
        themes = [fallback_theme] if fallback_theme else []

    title = re.sub(r"^RERC Partner Community:\s*", "", title, flags=re.I)
    source_url = public_url(source.get("origin_path_or_url"))
    year = year_for(case, program_name)
    if program_name in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"} or not summary_is_public_ready(summary, title):
        summary = fallback_summary(title, program_name, place, state, themes, year)
    if summary[-1] not in ".!?":
        summary += "."
    item_id = "RERC-CASE-" + re.sub(r"[^A-Z0-9]+", "-", compact(case.get("case_id")).upper()).strip("-")
    return {
        "item_id": item_id,
        "item_type": "Case Study",
        "title": title,
        "organization": program_name,
        "status": (
            "Planning assistance example"
            if program_name in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"}
            else "Published case study"
        ),
        "last_checked": checked_on,
        "geography": state,
        "eligible_users": "Communities looking for comparable examples",
        "project_stage": stage_for(case, program_name, source_url),
        "topic_tags": "; ".join(themes),
        "support_type": "Case study",
        "amount_or_cost": "",
        "match_or_cost": "",
        "deadline_or_availability": year,
        "summary": summary,
        "why_it_matters": "",
        "source_url": source_url,
        "case_place": place,
        "case_state": state,
        "case_place_type": normalized_place_type(case, place, state),
        "case_program": program_name,
        "case_year": year,
        "case_partners": "; ".join(
            item for item in (repair_text(value) for value in case.get("partners", [])[:5])
            if item and len(item) <= 90 and "$" not in item
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a public-safe RERC case-study projection from Protos.")
    parser.add_argument("--protos-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checked-on", default=date.today().isoformat())
    args = parser.parse_args()

    case_root = args.protos_root / "data" / "cases"
    records = [
        record
        for path in sorted(case_root.rglob("case.json"))
        if (record := build_record(path, args.checked_on))
    ]
    records.sort(key=lambda item: (item["case_state"], item["case_place"], item["title"]))
    serialized = json.dumps(
        {
            "generated_at": args.checked_on,
            "provenance": "Official federal community examples with public links; no images or private administrative fields.",
            "items": records,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if re.search(r"[A-Z]:\\|Z:\\|D:\\", serialized, flags=re.I):
        raise RuntimeError("Public case-study bundle contains a local Windows path.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("window.RERC_CASE_STUDIES=" + serialized + ";\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "PASS", "count": len(records), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
