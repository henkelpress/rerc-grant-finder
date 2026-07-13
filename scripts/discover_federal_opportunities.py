from __future__ import annotations

import csv
import json
import re
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_JS = ROOT / "data.js"
API_URL = "https://api.grants.gov/v1/api/search2"
SEARCH_TERMS = (
    "rural development",
    "outdoor recreation",
    "recreational trails",
    "tourism",
    "community development",
    "economic development",
    "technical assistance",
)
OUTPUT_CSV = ROOT / "federal-opportunity-review-queue.csv"
OUTPUT_MD = ROOT / "federal-opportunity-review-queue.md"


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def load_current_titles() -> set[str]:
    raw = DATA_JS.read_text(encoding="utf-8").strip()
    formats = (
        ("window.RERC_CATALOG = ", "items", "title"),
        ("window.GRANT_EXPLORER_DATA = ", "grants", "grant_name"),
    )
    for prefix, collection_key, title_key in formats:
        if raw.startswith(prefix) and raw.endswith(";"):
            data = json.loads(raw[len(prefix) : -1])
            return {
                normalize(str(item.get(title_key, "")))
                for item in data.get(collection_key, [])
                if str(item.get(title_key, "")).strip()
            }
    raise ValueError("data.js is not in a recognized public catalog format")


def search(term: str) -> list[dict]:
    payload = json.dumps(
        {
            "rows": 100,
            "keyword": term,
            "oppNum": "",
            "eligibilities": "",
            "agencies": "",
            "oppStatuses": "forecasted|posted",
            "aln": "",
            "fundingCategories": "",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "RERC-Funding-Resource-Explorer/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("errorcode") not in {0, "0", None}:
        raise RuntimeError(result.get("msg") or f"Grants.gov returned error {result.get('errorcode')}")
    return result.get("data", {}).get("oppHits", [])


def main() -> int:
    current_titles = load_current_titles()
    found: dict[str, dict] = {}
    matched_terms: defaultdict[str, set[str]] = defaultdict(set)
    errors: list[str] = []

    for term in SEARCH_TERMS:
        try:
            hits = search(term)
        except Exception as exc:  # noqa: BLE001 - preserve a useful partial queue when one search fails.
            errors.append(f"{term}: {type(exc).__name__}: {exc}")
            continue
        for hit in hits:
            key = str(hit.get("id") or hit.get("number") or hit.get("title") or "").strip()
            if not key:
                continue
            found[key] = hit
            matched_terms[key].add(term)

    rows = []
    for key, hit in found.items():
        title = str(hit.get("title") or "").strip()
        opportunity_id = str(hit.get("id") or "").strip()
        rows.append(
            {
                "review_status": "Possible catalog match" if normalize(title) in current_titles else "Review for addition",
                "opportunity_title": title,
                "opportunity_number": str(hit.get("number") or "").strip(),
                "agency": str(hit.get("agencyName") or hit.get("agencyCode") or "").strip(),
                "opportunity_status": str(hit.get("oppStatus") or "").strip(),
                "open_date": str(hit.get("openDate") or "").strip(),
                "close_date": str(hit.get("closeDate") or "").strip(),
                "matched_searches": "; ".join(sorted(matched_terms[key])),
                "official_url": f"https://www.grants.gov/search-results-detail/{opportunity_id}" if opportunity_id else "",
                "screening_note": "Human review is required before publication.",
            }
        )
    rows.sort(key=lambda row: (row["review_status"], row["close_date"], row["opportunity_title"]))

    fieldnames = [
        "review_status",
        "opportunity_title",
        "opportunity_number",
        "agency",
        "opportunity_status",
        "open_date",
        "close_date",
        "matched_searches",
        "official_url",
        "screening_note",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    new_count = sum(row["review_status"] == "Review for addition" for row in rows)
    lines = [
        "# Federal Opportunity Review Queue",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Candidates found: {len(rows)}",
        f"Review for possible addition: {new_count}",
        f"Possible catalog title matches: {len(rows) - new_count}",
        f"Search errors: {len(errors)}",
        "",
        "This is a review queue. No record is added to the public catalog automatically.",
        "",
    ]
    if errors:
        lines.extend(["## Search Errors", "", *[f"- {error}" for error in errors], ""])
    lines.extend(["## First 50 Candidates", ""])
    for row in rows[:50]:
        lines.append(
            f"- [{row['opportunity_title']}]({row['official_url']}) | {row['agency']} | "
            f"{row['opportunity_status']} | closes {row['close_date'] or 'not listed'}"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(rows), "review_for_addition": new_count, "search_errors": errors}, indent=2))
    return 1 if not rows and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
