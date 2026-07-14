from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "window.RERC_CATALOG = "


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    run(sys.executable, "-m", "py_compile", "rercie/rercie_core.py", "rercie/rercie_quality.py", "rercie/rercie.py")
    run(sys.executable, "rercie/rercie.py", "--smoke")
    run("node", "--check", "app.js")

    raw = (ROOT / "data.js").read_text(encoding="utf-8").strip()
    assert raw.startswith(PREFIX) and raw.endswith(";")
    payload = json.loads(raw[len(PREFIX):-1])
    items = payload["items"]
    counts = payload["counts"]
    assert counts == {
        "combined": len(items),
        "funding": sum(item["item_type"] == "Funding" for item in items),
        "resources": sum(item["item_type"] == "Resource" for item in items),
    }
    by_id = {item["item_id"]: item for item in items}
    for item_id in ("RERC-RES-0014", "RERC-RES-0066", "RERC-RES-0068", "RERC-RES-0076"):
        assert by_id[item_id]["item_type"] == "Funding"
    assert all(item["item_type"] in {"Funding", "Resource"} for item in items)
    assert not any(re.search(r"potential rerc fit|purpose tags", item.get("why_it_matters", ""), re.I) for item in items)
    assert not any((item.get("summary") or "").strip() in {"", "-"} for item in items)

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    for label in (">Both<", ">Funding<", ">Resources<"):
        assert label in index
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert "item.eligible_users" in app
    assert "confirm territory eligibility" in app
    assert "selectedStage !== \"Any step\"" in app

    core = (ROOT / "rercie" / "rercie_core.py").read_text(encoding="utf-8")
    assert "call_openai_compatible" not in core
    assert "apiEndpoint" not in core and "apiModel" not in core
    assert "RERCie is generating a draft with local Gemma" in core
    launcher = (ROOT / "rercie" / "packaging" / "RERCieLauncher.cs").read_text(encoding="utf-8")
    assert "Read the Gemma Terms" in launcher
    assert "Apache License 2.0" not in launcher

    sys.path.insert(0, str(ROOT / "rercie"))
    import rercie as app
    profile = {"population": "1046", "source": "Test source"}
    unsafe = "The town will acquire land, hire a consultant, obtain approvals, and has strong community support."
    assert app.app.grounding_issues(unsafe, {"projectSummary": "Improve a trail."}, profile)
    scaffold = app.app.deterministic_scaffold(
        {"community": "Test", "state": "Virginia", "projectTitle": "Trail", "projectSummary": "Improve a trail."},
        profile,
    )
    assert not app.app.grounding_issues(
        scaffold,
        {"community": "Test", "state": "Virginia", "projectTitle": "Trail", "projectSummary": "Improve a trail."},
        profile,
    )

    result = {"status": "PASS", "version": app.app.APP_VERSION, "counts": counts, "checks": 18}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
