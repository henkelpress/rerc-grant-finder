from __future__ import annotations

import concurrent.futures
import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_JS = ROOT / "data.js"
JSON_PREFIX = "window.GRANT_EXPLORER_DATA = "
TIMEOUT_SECONDS = 20
MAX_WORKERS = 12


def load_urls() -> list[str]:
    raw = DATA_JS.read_text(encoding="utf-8").strip()
    if not raw.startswith(JSON_PREFIX) or not raw.endswith(";"):
        raise ValueError("data.js is not in the expected public site format")
    data = json.loads(raw[len(JSON_PREFIX) : -1])
    urls = sorted({grant.get("url", "").strip() for grant in data.get("grants", []) if grant.get("url", "").strip()})
    return urls


def probe(url: str) -> dict:
    start = time.time()
    result = {"url": url, "ok": False, "status": None, "error": "", "elapsed_seconds": None}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}
    context = ssl.create_default_context()
    for method in ("HEAD", "GET"):
        try:
            request = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:
                status = getattr(response, "status", 200)
                result.update({"ok": status < 400, "status": status, "error": ""})
                break
        except urllib.error.HTTPError as exc:
            if method == "HEAD":
                continue
            result.update({"ok": False, "status": exc.code, "error": str(exc)})
            break
        except Exception as exc:  # noqa: BLE001 - scheduled public health report should capture varied URL failures.
            if method == "HEAD":
                continue
            result.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
            break
    result["elapsed_seconds"] = round(time.time() - start, 2)
    return result


def main() -> int:
    urls = load_urls()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(probe, urls))
    failed = [item for item in results if not item["ok"]]
    report = {
        "status": "PASS" if not failed else "REVIEW",
        "unique_urls_checked": len(urls),
        "failed_urls": len(failed),
        "results": results,
    }
    (ROOT / "source-health-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Source Health Report", "", f"Unique source links checked: {len(urls)}", f"Links needing review: {len(failed)}", ""]
    if failed:
        lines.append("## Links Needing Review")
        for item in failed[:100]:
            lines.append(f"- {item['status'] or 'error'}: {item['url']} ({item['error']})")
    (ROOT / "source-health-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"unique_urls_checked": len(urls), "failed_urls": len(failed)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
