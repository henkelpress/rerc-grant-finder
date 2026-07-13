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
TIMEOUT_SECONDS = 20
MAX_WORKERS = 12


def load_urls() -> list[str]:
    raw = DATA_JS.read_text(encoding="utf-8").strip()
    formats = (
        ("window.RERC_CATALOG = ", "items", "source_url"),
        ("window.GRANT_EXPLORER_DATA = ", "grants", "url"),
    )
    for prefix, collection_key, url_key in formats:
        if raw.startswith(prefix) and raw.endswith(";"):
            data = json.loads(raw[len(prefix) : -1])
            return sorted(
                {
                    str(item.get(url_key, "")).strip()
                    for item in data.get(collection_key, [])
                    if str(item.get(url_key, "")).strip()
                }
            )
    raise ValueError("data.js is not in a recognized public catalog format")


def probe(url: str) -> dict:
    start = time.time()
    result = {"url": url, "ok": False, "status": None, "error": "", "elapsed_seconds": None}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
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
        except Exception as exc:  # noqa: BLE001 - scheduled report records varied provider failures.
            if method == "HEAD":
                continue
            result.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
            break
    result["elapsed_seconds"] = round(time.time() - start, 2)
    return result


def is_hard_failure(item: dict) -> bool:
    status = item.get("status")
    return isinstance(status, int) and status not in {403} and status >= 400


def needs_manual_review(item: dict) -> bool:
    return not item["ok"] and not is_hard_failure(item)


def main() -> int:
    urls = load_urls()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(probe, urls))
    failed = [item for item in results if is_hard_failure(item)]
    manual_review = [item for item in results if needs_manual_review(item)]
    bot_blocked = [item for item in manual_review if item.get("status") == 403]
    report = {
        "status": "PASS" if not failed else "REVIEW",
        "unique_urls_checked": len(urls),
        "failed_urls": len(failed),
        "manual_review_urls": len(manual_review),
        "bot_blocked_urls": len(bot_blocked),
        "results": results,
    }
    (ROOT / "source-health-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Source Health Report",
        "",
        f"Unique source links checked: {len(urls)}",
        f"Hard failures: {len(failed)}",
        f"Manual review URLs: {len(manual_review)}",
        f"Bot-blocked URLs: {len(bot_blocked)}",
        "",
    ]
    if failed:
        lines.append("## Hard Failures")
        lines.extend(f"- {item['status'] or 'error'}: {item['url']} ({item['error']})" for item in failed[:100])
    if manual_review:
        lines.append("## Manual Review")
        lines.extend(
            f"- {item['status'] or 'error'}: {item['url']} ({item['error']})" for item in manual_review[:100]
        )
    (ROOT / "source-health-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "unique_urls_checked": len(urls),
                "failed_urls": len(failed),
                "manual_review_urls": len(manual_review),
                "bot_blocked_urls": len(bot_blocked),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
