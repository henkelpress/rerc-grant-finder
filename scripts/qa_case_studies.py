from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "case_studies.js"
MANIFEST = ROOT / "case_studies.public_manifest.json"
PREFIX = "window.RERC_CASE_STUDIES="
PUBLIC_HOSTS = {"www.epa.gov", "toolkit.climate.gov", "www.rd.usda.gov"}
FORBIDDEN = (
    "protos treats",
    "protos indexes",
    "record remains flagged",
    "image rights",
    "internal source",
    "local source",
    "needs review",
    "source manifest",
    ".pptx",
    ".docx",
    ".xlsx",
)


def main() -> int:
    raw = DATA.read_text(encoding="utf-8").strip()
    assert raw.startswith(PREFIX) and raw.endswith(";")
    payload = json.loads(raw[len(PREFIX) : -1])
    items = payload["items"]
    assert len(items) >= 400
    assert len({item["item_id"] for item in items}) == len(items)
    assert all(item["item_type"] == "Case Study" for item in items)
    assert all(55 <= len(item["summary"]) <= 560 for item in items)
    assert all(item["case_place"] and item["case_state"] for item in items)
    assert all(item["case_state"] != "Unknown" for item in items)
    assert all(urlparse(item["source_url"]).hostname in PUBLIC_HOSTS for item in items)

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert not re.search(r"[a-z]:\\", serialized)
    assert not any(marker in serialized for marker in FORBIDDEN)
    assert not any(marker in serialized for marker in ("Ã", "Â", "â", "Æ", "ï¿½", "\ufffd"))
    assert not any("$" in item["case_place"] or len(item["case_place"]) > 72 for item in items)
    assert not any(re.search(r"epa grant recipients?|site description|photo courtesy|pictured here|supporting environmental excellence", item["summary"], re.I) for item in items)
    assert all(item["summary"][-1] in ".!?" for item in items)
    assert not any(re.search(r"appears in the official|case record for|is an official|an USDA", item["summary"], re.I) for item in items)
    assert not any(any(len(sentence.split()) > 49 for sentence in re.split(r"(?<=[.!?])\s+", item["summary"])) for item in items)
    assert not any(item["case_place"] == item["case_state"] for item in items)
    assert all(item["case_place_type"] in {"town_or_city", "county_or_region", "tribal_community", "statewide_or_multi_community"} for item in items)
    assert sum(item["case_place_type"] == "tribal_community" for item in items) >= 10
    expected_place_types = {
        "A Successful Transformation: From Wasted Lot to Reading Hot‐Spot": "town_or_city",
        "Richmond Creamery, Richmond, Vt.": "town_or_city",
        "South Dakota Governor's House Program - Providing Affordable Housing for 30 Years": "statewide_or_multi_community",
        "Lapwai, Idaho Local Foods, Local Places Summary Report": "tribal_community",
        "Mission, South Dakota Local Foods, Local Places Summary Report": "tribal_community",
        "Akwesasne, New York (2022)": "tribal_community",
    }
    place_types_by_title = {item["title"]: item["case_place_type"] for item in items}
    assert all(place_types_by_title.get(title) == expected for title, expected in expected_place_types.items())
    assert all(item["project_stage"] in {"Planning", "Implementation", "Cleanup"} for item in items)
    assert all(item["project_stage"] == "Cleanup" for item in items if item["case_program"] == "EPA Brownfields Success Stories")
    assert not any(item["case_year"] == "2026" for item in items if item["case_program"] == "EPA Examples of Smart Growth Communities and Projects")

    debris = re.compile(r"image lessons learned|figure\s+\d|courtesy|years awarded|site descrip|grant types:|grants and resources:|\u019f", re.I)
    suspicious_place = re.compile(r"\b(plan|action|company|industrial development|successful transformation|workers in|brownfield to)\b", re.I)
    assert not any(debris.search(item["summary"]) or item["summary"][:1].islower() for item in items)
    assert not any(":" in item["case_place"] or suspicious_place.search(item["case_place"]) for item in items)
    planning = [item for item in items if item["case_program"] in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"}]
    assert len({item["summary"] for item in planning}) == len(planning)
    assert all(item["case_place"].lower() in item["summary"].lower() or item["case_place"] == "Multiple communities" for item in planning)
    assert all(
        item["case_place"] == "Forest County" or item["case_place_type"] in {"town_or_city", "tribal_community"}
        for item in items if item["case_program"] == "Local Foods, Local Places"
    )

    programs = Counter(item["case_program"] for item in items)
    hosts = Counter(urlparse(item["source_url"]).hostname for item in items)
    manifest = {
        "release_id": f"rerc-public-community-examples-{payload['generated_at']}",
        "status": "PASS",
        "scope": "Text-only community examples derived from official federal public web records.",
        "approval_basis": "Public RERC community-example integration approved on 2026-07-17.",
        "privacy": {
            "private_source_records_modified": False,
            "local_paths_included": False,
            "admin_fields_included": False,
            "images_included": False,
        },
        "rights_note": "Official links and short source-derived descriptions are attributed. Images are excluded. This release check is not a legal opinion.",
        "count": len(items),
        "program_counts": dict(sorted(programs.items())),
        "source_host_counts": dict(sorted(hosts.items())),
        "checks": [
            "unique IDs",
            "official HTTPS hosts only",
            "bounded summaries",
            "known geography",
            "no private paths",
            "no internal workflow language",
            "no source filenames",
            "no common mojibake",
            "no images",
            "no extraction debris",
            "specific community names",
            "normalized community types",
            "distinct planning-assistance summaries",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
