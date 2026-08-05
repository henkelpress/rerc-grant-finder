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
            actual_match = place in item["covered_states"]
            assert actual_match == should_match, f"{item_id}: coverage matrix leak for {place}"
            matrix_checks += 1

    nonregional_with_coverage = [
        item["item_id"] for item in items
        if str(item.get("geography", "")).strip().lower() != "multi-state" and item.get("covered_states")
    ]
    assert not nonregional_with_coverage, f"Unexpected covered_states outside Multi-State: {nonregional_with_coverage[:10]}"
    print(json.dumps({
        "status": "PASS",
        "regional_records": len(regional),
        "supported_places": len(SUPPORTED),
        "coverage_matrix_checks": matrix_checks,
        "unresolved_records": 0,
        "leaks": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())