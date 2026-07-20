from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
import re
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
PREFIX = "window.RERC_CATALOG = "
MAX_REVIEW_AGE_DAYS = 60
DATE_RE = re.compile(
    r"\b20\d{2}-\d{1,2}-\d{1,2}\b|"
    r"\b\d{1,2}/\d{1,2}/20\d{2}\b|"
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+"
    r"\d{1,2}(?:st|nd|rd|th)?(?:\s*[-\u2013\u2014]\s*\d{1,2})?,?\s+20\d{2}\b",
    re.I,
)
ANNUAL_DATE_RE = re.compile(
    r"\b(?:deadline|due|closes?|closing|applications? accepted|application)\b[^.;]{0,50}"
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2}\b|"
    r"\b20\d{2}\s+deadlines?\b[^.;]{0,100}",
    re.I,
)
ROLLING_RE = re.compile(
    r"\b(rolling|ongoing|year[- ]round|continuous|always open|open throughout the year|"
    r"no fixed deadlines?|first[- ]come,? first[- ]served|as needed|while (?:funding|funds) remain|"
    r"until funds? (?:are )?depleted|applications? (?:are )?accepted (?:throughout|year[- ]round))\b",
    re.I,
)
CLOSED_RE = re.compile(
    r"\b(cycle closed|round closed|has ended|ended|awarded|wrapped|not accepting|no current round|"
    r"next round|future round|deadline passed)\b",
    re.I,
)
VARIABLE_RE = re.compile(
    r"\b(deadlines? vary|cycles? vary|var(?:y|ies) by|fund-specific|region(?:al)? deadlines?|"
    r"multiple .* cycles|category-specific|program-specific|local deadlines?)\b",
    re.I,
)
ACTIVE_RE = re.compile(
    r"\b(tax years?|program years?|operates? from|active through|reauthorized through|fiscal year|"
    r"incentive year|funding availability applies)\b",
    re.I,
)
RECURRING_RE = re.compile(
    r"\b(recurring|annual|biennial|two-year cycle|periodic|quarterly|monthly|spring cycle|"
    r"summer cycle|fall cycle|winter cycle|grant cycle|application cycle|competitive rounds?)\b",
    re.I,
)


def load_catalog(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw.startswith(PREFIX) or not raw.endswith(";"):
        raise ValueError("data.js is not in the RERC catalog format")
    return json.loads(raw[len(PREFIX) : -1])


def classify(item: dict) -> str:
    timing = str(item.get("deadline_or_availability") or "").strip()
    combined = f"{item.get('status', '')} {timing}"
    if DATE_RE.search(timing) or ANNUAL_DATE_RE.search(timing):
        return "dated"
    if ROLLING_RE.search(timing):
        return "rolling"
    if CLOSED_RE.search(combined):
        return "closed"
    if VARIABLE_RE.search(timing):
        return "variable"
    if ACTIVE_RE.search(timing):
        return "active_period"
    if RECURRING_RE.search(combined):
        return "recurring"
    return "date_pending"


def audit(path: Path) -> dict:
    payload = load_catalog(path)
    funding = [item for item in payload.get("items", []) if item.get("item_type") == "Funding"]
    rows = []
    issues = []
    counts: Counter[str] = Counter()
    today = date.today()
    for item in funding:
        timing = str(item.get("deadline_or_availability") or "").strip()
        checked = str(item.get("last_checked") or "").strip()
        source = str(item.get("source_url") or "").strip()
        category = classify(item)
        counts[category] += 1
        checked_date = date.fromisoformat(checked) if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", checked) else None
        row = {
            "item_id": item.get("item_id"),
            "title": item.get("title"),
            "status": item.get("status"),
            "timing_class": category,
            "deadline_or_availability": timing,
            "last_checked": checked,
            "review_age_days": (today - checked_date).days if checked_date else None,
            "source_url": source,
        }
        rows.append(row)
        if not timing:
            issues.append({"item_id": item.get("item_id"), "issue": "blank timing"})
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", checked):
            issues.append({"item_id": item.get("item_id"), "issue": "missing review date"})
        if not source.startswith("https://"):
            issues.append({"item_id": item.get("item_id"), "issue": "missing HTTPS source"})
    expected = {"dated", "rolling", "closed", "variable", "active_period", "recurring", "date_pending"}
    if set(counts) - expected:
        issues.append({"issue": "unexpected timing class", "values": sorted(set(counts) - expected)})
    stale = [row for row in rows if row["review_age_days"] is not None and row["review_age_days"] > MAX_REVIEW_AGE_DAYS]
    return {
        "status": "PASS" if not issues and len(funding) == 659 and not stale else "FAIL",
        "coverage_status": "PASS" if not issues and len(funding) == 659 else "FAIL",
        "freshness_status": "REVIEW" if stale else "CURRENT",
        "checked_on": today.isoformat(),
        "funding_records": len(funding),
        "counts": dict(sorted(counts.items())),
        "records_with_timing": sum(bool(row["deadline_or_availability"]) for row in rows),
        "records_with_review_date": sum(bool(re.fullmatch(r"20\d{2}-\d{2}-\d{2}", row["last_checked"])) for row in rows),
        "records_with_https_source": sum(row["source_url"].startswith("https://") for row in rows),
        "freshness_policy_days": MAX_REVIEW_AGE_DAYS,
        "stale_over_policy_days": len(stale),
        "oldest_review_date": min((row["last_checked"] for row in rows if row["last_checked"]), default=""),
        "stale_review_queue": stale,
        "review_queue": [row for row in rows if row["timing_class"] in {"variable", "recurring", "active_period", "date_pending"}],
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit deadline and rolling-status coverage for every public funding record.")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    data_path = ROOT / "data.js"
    if not data_path.exists():
        data_path = ROOT / "site-src" / "data.js"
    report = audit(data_path)
    if args.write_report:
        (ROOT / "funding-deadline-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        lines = [
            "# Funding Deadline Audit",
            "",
            f"Status: {report['status']}",
            f"Funding records: {report['funding_records']}",
            f"Timing fields present: {report['records_with_timing']}",
            f"Review dates present: {report['records_with_review_date']}",
            f"HTTPS sources present: {report['records_with_https_source']}",
            f"Freshness status: {report['freshness_status']}",
            f"Freshness policy: review source content at least every {report['freshness_policy_days']} days",
            f"Reviews beyond policy: {report['stale_over_policy_days']}",
            f"Oldest review date: {report['oldest_review_date']}",
            "",
            "Coverage confirms that every record has timing text, a review date, and an HTTPS source. The daily source monitor checks link and page-change signals; this audit fails when a record exceeds the content-review policy.",
            "",
            "## Timing Classes",
        ]
        lines.extend(f"- {name}: {count}" for name, count in report["counts"].items())
        lines.extend(["", f"Records queued for a future date check: {len(report['review_queue'])}"])
        (ROOT / "funding-deadline-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "coverage_status", "freshness_status", "funding_records", "counts", "records_with_timing", "records_with_review_date", "records_with_https_source", "freshness_policy_days", "stale_over_policy_days", "oldest_review_date", "issues")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
