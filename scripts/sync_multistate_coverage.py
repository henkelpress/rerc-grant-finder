from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "window.RERC_CATALOG = "


def load_catalog() -> dict:
    raw = (ROOT / "data.js").read_text(encoding="utf-8").strip()
    if not raw.startswith(PREFIX) or not raw.endswith(";"):
        raise ValueError("Unexpected data.js format")
    return json.loads(raw[len(PREFIX):-1])


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync reviewed Multi-State coverage into data.js")
    parser.add_argument("--write", action="store_true", help="write reviewed manifest values into data.js")
    args = parser.parse_args()

    catalog = load_catalog()
    manifest = json.loads((ROOT / "maintenance" / "multistate_coverage.json").read_text(encoding="utf-8"))
    rows = manifest["records"]
    by_id = {row["item_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate item_id in coverage manifest")
    regional = [item for item in catalog["items"] if str(item.get("geography", "")).strip().lower() == "multi-state"]
    regional_ids = {item["item_id"] for item in regional}
    if regional_ids != set(by_id):
        raise ValueError(json.dumps({"missing_manifest": sorted(regional_ids - set(by_id)), "extra_manifest": sorted(set(by_id) - regional_ids)}))

    changed = 0
    for item in regional:
        row = by_id[item["item_id"]]
        expected = {
            "covered_states": row["covered_states"],
            "coverage_note": row["coverage_note"],
            "coverage_source_url": row["coverage_source_url"],
        }
        if any(item.get(key) != value for key, value in expected.items()):
            changed += 1
            if args.write:
                item.update(expected)

    if args.write:
        (ROOT / "data.js").write_text(PREFIX + json.dumps(catalog, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8")
    elif changed:
        raise SystemExit(f"Coverage manifest differs from data.js for {changed} records. Run with --write.")

    print(json.dumps({"status": "PASS", "mode": "write" if args.write else "check", "regional_records": len(regional), "changed": changed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())