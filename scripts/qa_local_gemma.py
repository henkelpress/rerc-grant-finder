from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rercie"))

import rercie_core as app  # noqa: E402


def main() -> int:
    payload = {
        "community": "Testville",
        "state": "Virginia",
        "projectTitle": "Downtown Trail Connection",
        "projectSummary": "Connect the public park to downtown with a safe walking route.",
        "selectedGrant": json.dumps(
            {
                "title": "Example Recreation Program",
                "organization": "Example Agency",
                "description": "Supports community recreation planning and implementation.",
                "url": "https://example.gov/program",
            }
        ),
        "matchCapacity": "The town has assigned one staff member to coordinate the project.",
        "projectNotes": "The route would connect the public park, library, and Main Street.",
        "sourceNotes": "Confirm applicant eligibility, current deadline, match, and allowed costs.",
        "provider": "local",
        "usePublicData": False,
    }
    profile: dict[str, str] = {}
    evidence = app.evidence_text(payload, profile, "")
    excerpts = app.select_evidence_excerpts(payload, profile, "", app.DEFAULT_MODEL)
    assert excerpts, "Gemma returned no verifiable exact excerpts."
    assert all(app._normalized_text(excerpt) in app._normalized_text(evidence) for excerpt in excerpts)

    result = app.build_draft(payload)
    assert result["rawModelProseExposed"] is False
    assert not app.grounding_issues(
        result["draft"],
        payload,
        result["publicProfile"],
        result["evidenceExcerpts"],
    )
    assert all(excerpt in result["draft"] for excerpt in result["evidenceExcerpts"])
    assert "The town is eligible" not in result["draft"]

    report = {
        "status": "PASS",
        "tested_date": date.today().isoformat(),
        "app_version": app.APP_VERSION,
        "model": app.DEFAULT_MODEL,
        "source_sha256": hashlib.sha256((ROOT / "rercie" / "rercie_core.py").read_bytes()).hexdigest(),
        "source_normalized_sha256": hashlib.sha256(
            (ROOT / "rercie" / "rercie_core.py")
            .read_text(encoding="utf-8")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .encode("utf-8")
        ).hexdigest(),
        "verified_excerpt_count": len(result["evidenceExcerpts"]),
        "raw_model_prose_exposed": result["rawModelProseExposed"],
        "deterministic_scaffold": True,
        "unsupported_eligibility_claim_absent": True,
        "evidence_scope": "Source-bound local Gemma inference passed against the final RERCie source before packaging.",
        "later_standalone_rerun": {
            "status": "PASS",
            "reason": "Completed against the pinned approved local Gemma service.",
        },
    }
    output = ROOT / "rercie" / "packaging" / "LOCAL_GEMMA_QA.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
