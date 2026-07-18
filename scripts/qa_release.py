from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "window.RERC_CATALOG = "


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    run(sys.executable, "-m", "py_compile", "rercie/rercie_core.py", "rercie/rercie_quality.py", "rercie/rercie.py")
    run(sys.executable, "rercie/rercie.py", "--smoke")
    run("node", "--check", "app.js")
    run(sys.executable, "scripts/qa_case_studies.py")

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
    for label in (">All<", ">Funding<", ">Resources<", ">Case studies<"):
        assert label in index
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert "item.eligible_users" in app
    assert "confirm territory eligibility" in app
    assert "selectedStage !== \"Any step\"" in app
    assert "counties" in app and "cities" in app
    assert 'stageText !== "mixed"' not in app
    assert "View program details" in app and "Open the resource" in app
    assert "source-backed examples from Protos" not in index
    assert "window.RERC_CASE_STUDIES" in app
    assert "Read the example" in app
    assert "placeTypeSelect" in index

    case_raw = (ROOT / "case_studies.js").read_text(encoding="utf-8").strip()
    case_prefix = "window.RERC_CASE_STUDIES="
    assert case_raw.startswith(case_prefix) and case_raw.endswith(";")
    cases = json.loads(case_raw[len(case_prefix):-1])["items"]
    assert len(cases) == 477
    assert all(case["source_url"].startswith(("https://www.epa.gov/", "https://toolkit.climate.gov/", "https://www.rd.usda.gov/")) for case in cases)
    assert not any(re.search(r"[A-Za-z]:\\\\|protos|private_internal|needs_image_review", json.dumps(case), re.I) for case in cases)

    downloads = ROOT / "downloads"
    static_docx = downloads / "RERC_Community_Explorer_Appendix_2026-07-18.docx"
    static_xlsx = downloads / "RERC_Community_Explorer_Master_2026-07-18.xlsx"
    static_csv = downloads / "RERC_Community_Explorer_Master_2026-07-18.csv"
    assert static_docx.stat().st_size > 100_000
    assert static_xlsx.stat().st_size > 100_000
    assert static_csv.stat().st_size > 100_000
    assert len(static_csv.read_text(encoding="utf-8-sig").splitlines()) == 1198
    with zipfile.ZipFile(static_docx) as package:
        names = set(package.namelist())
        assert "word/comments.xml" not in names
        document_xml = package.read("word/document.xml").decode("utf-8")
        assert document_xml.count("<w:hyperlink") == 1197
    with zipfile.ZipFile(static_xlsx) as package:
        names = set(package.namelist())
        assert not any(name.startswith("xl/comments") for name in names)
        workbook_xml = package.read("xl/workbook.xml").decode("utf-8")
        assert all(name in workbook_xml for name in ("Funding", "Resources", "Community Examples"))
    sha256 = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    package_report = json.loads((downloads / "RERC_Community_Explorer_QA_2026-07-18.json").read_text(encoding="utf-8"))
    assert package_report["status"] == "PASS"
    assert package_report["source_sha256"] == {
        "data.js": sha256(ROOT / "data.js"),
        "case_studies.js": sha256(ROOT / "case_studies.js"),
    }
    assert package_report["docx"]["sha256"] == sha256(static_docx)
    assert package_report["xlsx"]["sha256"] == sha256(static_xlsx)
    assert package_report["csv"]["sha256"] == sha256(static_csv)

    source_health = json.loads((ROOT / "case_studies.source_health.json").read_text(encoding="utf-8"))
    assert source_health["status"] == "PASS" and source_health["unique_urls"] == 304
    assert source_health["counts"]["hard_failure"] == 0
    assert source_health["case_studies_sha256"] == hashlib.sha256((ROOT / "case_studies.js").read_bytes()).hexdigest()

    core = (ROOT / "rercie" / "rercie_core.py").read_text(encoding="utf-8")
    assert "call_openai_compatible" not in core
    assert "apiEndpoint" not in core and "apiModel" not in core
    assert "RERCie is reviewing your notes with local Gemma" in core
    assert "rawModelProseExposed" in core
    assert "parse_verified_excerpts" in core
    launcher = (ROOT / "rercie" / "packaging" / "RERCieLauncher.cs").read_text(encoding="utf-8")
    assert "Read the Gemma Terms" in launcher
    assert "Apache License 2.0" not in launcher
    installer_script = (ROOT / "rercie" / "packaging" / "RERCie.iss").read_text(encoding="utf-8")
    assert '[InstallDelete]' not in installer_script
    assert 'Name: "{app}\\models"' in installer_script  # Uninstall cleanup remains intentional.
    local_report = json.loads((ROOT / "rercie" / "packaging" / "LOCAL_GEMMA_QA.json").read_text(encoding="utf-8"))
    assert local_report["status"] == "PASS"
    assert local_report["app_version"] == "0.3.5"
    assert local_report["model"] == "gemma-3-1b-it-Q4_K_M.gguf"
    assert local_report["source_sha256"] == hashlib.sha256((ROOT / "rercie" / "rercie_core.py").read_bytes()).hexdigest()
    assert local_report["raw_model_prose_exposed"] is False

    sys.path.insert(0, str(ROOT / "rercie"))
    import rercie as app
    captured_urls = []
    original_request_json = app.app.request_json
    original_env_value = app.app._local_env_value
    app.app._local_env_value = lambda _name: ""
    app.app.request_json = lambda url, **_kwargs: (
        captured_urls.append(url)
        or [
            ["NAME", "DP05_0001E", "DP03_0062E", "DP03_0128PE", "DP05_0018E", "state", "place"],
            ["Taos town, New Mexico", "6458", "47304", "13.7", "53.7", "35", "76200"],
        ]
    )
    try:
        keyless_profile = app.app.fetch_census_community_profile("Taos", "New Mexico", "")
    finally:
        app.app.request_json = original_request_json
        app.app._local_env_value = original_env_value
    assert keyless_profile["place"] == "Taos town, New Mexico"
    assert captured_urls and "key=" not in captured_urls[0]

    profile = {"population": "1046", "source": "Test source"}
    draft_payload = {
        "community": "Test",
        "state": "Virginia",
        "projectTitle": "Trail",
        "projectSummary": "Improve a trail connection between the park and downtown.",
        "provider": "local",
        "usePublicData": False,
    }
    unsafe = "The town is eligible and will acquire land, hire a consultant, and secure every approval."
    assert app.app.grounding_issues(unsafe, draft_payload, profile)
    exact = "Improve a trail connection between the park and downtown."
    evidence = app.app.evidence_text(draft_payload, profile, "")
    verified = app.app.parse_verified_excerpts(json.dumps({"excerpts": [{"text": exact}]}), evidence)
    assert verified == [exact]
    paraphrased = app.app.parse_verified_excerpts(
        json.dumps({"excerpts": [{"text": "Build a trail from downtown to the park."}]}),
        evidence,
    )
    whitespace_changed = app.app.parse_verified_excerpts(
        json.dumps({"excerpts": [{"text": "Improve  a trail connection between the park and downtown."}]}),
        evidence,
    )
    assert paraphrased == []
    assert whitespace_changed == []
    scaffold = app.app.deterministic_scaffold(draft_payload, profile, verified)
    assert not app.app.grounding_issues(scaffold, draft_payload, profile, verified)
    original_selector = app.app.select_evidence_excerpts
    app.app.select_evidence_excerpts = lambda *_args, **_kwargs: [exact]
    try:
        built = app.app.build_draft(draft_payload)
    finally:
        app.app.select_evidence_excerpts = original_selector
    assert built["rawModelProseExposed"] is False
    assert built["evidenceExcerpts"] == [exact]
    assert exact in built["draft"]
    assert unsafe not in built["draft"]

    result = {
        "status": "PASS",
        "version": app.app.APP_VERSION,
        "counts": {**counts, "case_studies": len(cases), "public_total": len(items) + len(cases)},
        "checks": 59,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
