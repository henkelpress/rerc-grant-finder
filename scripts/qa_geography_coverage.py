from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "window.RERC_CATALOG = "
SUPPORTED = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
    "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "American Samoa",
    "Guam", "Northern Mariana Islands", "Puerto Rico", "U.S. Virgin Islands",
}


TERRITORIES = {"American Samoa", "Guam", "Northern Mariana Islands", "Puerto Rico", "U.S. Virgin Islands"}
APPALACHIAN = {
    "Alabama", "Georgia", "Kentucky", "Maryland", "Mississippi", "New York", "North Carolina",
    "Ohio", "Pennsylvania", "South Carolina", "Tennessee", "Virginia", "West Virginia",
}


def applies_to_place(geography: str, place: str) -> bool:
    import re
    for area in re.split(r"[;,|/]", geography):
        normalized = area.strip().casefold()
        selected = place.casefold()
        if normalized == selected or normalized.startswith(selected + " ("):
            return True
    return False


def is_national(geography: str) -> bool:
    value = geography.casefold()
    return any(term in value for term in ("national", "nationwide", "united states", "all states", "federal"))


def matches_geography(item: dict, place: str) -> bool:
    import re
    geography = str(item.get("geography", "")).strip()
    lowered = geography.casefold()
    covered = item.get("covered_states") or []
    if "multi-state" in lowered:
        return place in covered
    if covered:
        return place in covered
    if applies_to_place(geography, place):
        return True
    if is_national(geography):
        if place not in TERRITORIES:
            return True
        coverage_text = " ".join(str(item.get(field, "")) for field in ("geography", "eligible_users", "coverage_note")).casefold()
        return bool(re.search(r"territor|insular|island area", coverage_text) or re.search(r"(?<![a-z0-9])" + re.escape(place.casefold()) + r"(?![a-z0-9])", coverage_text))
    if "appalachian region" in lowered:
        return place in APPALACHIAN
    return False


def load_catalog() -> dict:
    raw = (ROOT / "data.js").read_text(encoding="utf-8").strip()
    if not raw.startswith(PREFIX) or not raw.endswith(";"):
        raise AssertionError("Unexpected data.js format")
    return json.loads(raw[len(PREFIX):-1])


def main() -> int:
    catalog = load_catalog()
    manifest = json.loads((ROOT / "maintenance" / "multistate_coverage.json").read_text(encoding="utf-8"))
    items = catalog["items"]
    regional = [item for item in items if str(item.get("geography", "")).strip().lower() == "multi-state"]
    by_id = {row["item_id"]: row for row in manifest["records"]}
    assert len(by_id) == len(manifest["records"]), "Duplicate manifest item_id"
    assert {item["item_id"] for item in regional} == set(by_id), "Manifest and catalog Multi-State IDs differ"

    matrix_checks = 0
    for item in regional:
        item_id = item["item_id"]
        states = item.get("covered_states")
        assert isinstance(states, list) and states, f"{item_id}: covered_states required"
        assert len(states) == len(set(states)), f"{item_id}: duplicate covered state"
        assert set(states) <= SUPPORTED, f"{item_id}: unsupported place {set(states) - SUPPORTED}"
        assert item.get("coverage_note", "").strip(), f"{item_id}: coverage_note required"
        assert str(item.get("coverage_source_url", "")).startswith("https://"), f"{item_id}: HTTPS coverage source required"
        assert states == by_id[item_id]["covered_states"], f"{item_id}: catalog coverage differs from manifest"
        assert item["coverage_note"] == by_id[item_id]["coverage_note"], f"{item_id}: coverage note differs"
        assert item["coverage_source_url"] == by_id[item_id]["coverage_source_url"], f"{item_id}: coverage source differs"
        for place in SUPPORTED:
            should_match = place in states
            actual_match = matches_geography(item, place)
            assert actual_match == should_match, f"{item_id}: coverage matrix leak for {place}"
            matrix_checks += 1

    nonregional_with_coverage = [
        item["item_id"] for item in items
        if str(item.get("geography", "")).strip().lower() != "multi-state" and item.get("covered_states")
    ]
    assert not nonregional_with_coverage, f"Unexpected covered_states outside Multi-State: {nonregional_with_coverage[:10]}"

    behavioral_checks = 0
    unmatched = []
    for item in items:
        matches = []
        for place in SUPPORTED:
            behavioral_checks += 1
            if matches_geography(item, place):
                matches.append(place)
        if not matches:
            unmatched.append(item["item_id"])
    assert not unmatched, f"Records unreachable after required location selection: {unmatched[:10]}"

    item_by_id = {item["item_id"]: item for item in items}
    assert matches_geography(item_by_id["RERC-FND-0269"], "New Jersey")
    assert matches_geography(item_by_id["RERC-FND-0269"], "New York")
    assert not matches_geography(item_by_id["RERC-FND-0269"], "Virginia")
    assert matches_geography(item_by_id["RERC-FND-0476"], "Puerto Rico")
    assert matches_geography(item_by_id["RERC-FND-0476"], "U.S. Virgin Islands")
    assert not matches_geography(item_by_id["RERC-FND-0476"], "Guam")
    for item_id in ("RERC-FND-0288", "RERC-FND-0287", "RERC-FND-0273", "RERC-RES-0037", "RERC-RES-0045"):
        for territory in TERRITORIES:
            assert matches_geography(item_by_id[item_id], territory), f"{item_id}: missing {territory}"
    for item_id in ("RERC-RES-NEW-2026-015", "RERC-RES-NEW-2026-018", "RERC-RES-NEW-2026-020", "RERC-RES-NEW-2026-031"):
        assert any(matches_geography(item_by_id[item_id], place) for place in SUPPORTED), f"{item_id}: unreachable"

    print(json.dumps({
        "status": "PASS",
        "regional_records": len(regional),
        "supported_places": len(SUPPORTED),
        "coverage_matrix_checks": matrix_checks,
        "behavior_matrix_checks": behavioral_checks,
        "unresolved_records": 0,
        "unreachable_records": 0,
        "leaks": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())