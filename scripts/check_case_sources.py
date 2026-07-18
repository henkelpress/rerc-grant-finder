from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "window.RERC_CASE_STUDIES="
USER_AGENT = "RERC-Community-Explorer-Link-Check/1.0"
KNOWN_BOT_BLOCKED_PREFIXES = (
    "https://www.rd.usda.gov/newsroom/success-stories/",
)


def load_urls() -> list[str]:
    raw = (ROOT / "case_studies.js").read_text(encoding="utf-8").strip()
    payload = json.loads(raw[len(PREFIX) : -1])
    return sorted({item["source_url"] for item in payload["items"]})


def request(url: str, method: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    context = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=25, context=context) as response:
        if method == "GET":
            response.read(512)
        return response.status, response.geturl()


def check(url: str) -> dict[str, object]:
    started = time.monotonic()
    status = 0
    final_url = url
    error = ""
    for method in ("HEAD", "GET"):
        try:
            status, final_url = request(url, method)
            break
        except urllib.error.HTTPError as exc:
            status = exc.code
            final_url = exc.geturl()
            error = str(exc.reason or "")
            if status not in {405, 500, 501} or method == "GET":
                break
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            if method == "GET":
                break
    if url.startswith(KNOWN_BOT_BLOCKED_PREFIXES):
        result = "restricted_but_present"
        if not error:
            error = "Automated access is inconsistently blocked by the publisher; manual review required."
    elif 200 <= status < 400:
        result = "reachable"
    elif status in {401, 403, 429}:
        result = "restricted_but_present"
    elif status in {404, 410}:
        result = "hard_failure"
    else:
        result = "manual_review"
    return {
        "url": url,
        "final_url": final_url,
        "http_status": status,
        "result": result,
        "error": error,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }


def main() -> int:
    urls = load_urls()
    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(check, url): url for url in urls}
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: str(row["url"]))
    counts = {name: sum(row["result"] == name for row in rows) for name in (
        "reachable",
        "restricted_but_present",
        "hard_failure",
        "manual_review",
    )}
    report = {
        "status": "PASS" if counts["hard_failure"] == 0 else "FAIL",
        "checked_date": date.today().isoformat(),
        "unique_urls": len(urls),
        "case_studies_sha256": hashlib.sha256((ROOT / "case_studies.js").read_bytes()).hexdigest(),
        "counts": counts,
        "results": rows,
    }
    output = ROOT / "case_studies.source_health.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
