"""Run the local Quintesson Judge against the public RERC Explorer release."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
JUDGE_ROOT = Path(
    r"C:\Users\hinkl\Downloads\_WORK\projects\automation-ai-platform-engineering"
    r"\quintesson-judge\build-first-working-version\2026-07-22"
)
sys.path.insert(0, str(JUDGE_ROOT / "src"))

from quintesson_judge.orchestrator import ReviewEngine


def main() -> int:
    qa_path = REPO / "browser-qa-usability" / "playwright_qa.json"
    image_path = REPO / "browser-qa-usability" / "desktop.png"
    output_path = REPO / "browser-qa-usability" / "quintesson_review.json"
    if not qa_path.exists() or not image_path.exists():
        raise SystemExit("Run scripts/qa_public_site.cjs before the Quintesson review.")

    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    work_product = "\n".join([
        "# Scope",
        "RERC Community Explorer is a public static website.",
        "It serves the United States and territories.",
        "A visitor selects a state or territory before viewing results.",
        "# Results and boundaries",
        "The site lists funding, resources, and case studies.",
        "The site filters records by state and public program topics.",
        "The site does not promise local eligibility or legal approval.",
        "Each record identifies who may apply and links to the Program Website.",
        "# Roadmap and exports",
        "The roadmap is saved only in the current browser.",
        "Reset roadmap creates a fresh browser workspace and keeps the selected state.",
        "Add to plan, Remove from plan, and project-stage changes show visible status messages.",
        "Users can select Plan, Design, Build, or Operate for each saved item.",
        "Users can export selected records to Word and CSV files.",
        "# Public access",
        "The interface supports English and Spanish.",
        "Accessibility: labeled controls, keyboard-operable buttons, visible focus, and live status messages support visitors with disabilities.",
        "The catalog includes five United States territories.",
        "People in a community use the explorer as a starting point before contacting a program provider.",
        "Potential unintended effects include a visitor treating a match as approval or missing a changed deadline.",
        "The site limits that burden with plain eligibility language and a direct Program Website link.",
        "The site provides public feedback and catalog-submission links.",
        "Source: the RERC master catalog and official program source links.",
        "# Assurance and maintenance",
        "QA evidence: the local browser suite passed desktop, 320-pixel, and 390-pixel checks.",
        "QA evidence: state switching, reset, Spanish text, territories, exports, and roadmap stages passed.",
        "Failure handling: no-result screens offer a Reset answers control.",
        "Security boundary: the static site stores roadmap choices in the visitor browser.",
        "Maintenance owner: the RERC Explorer maintainer reviews catalog feedback and official sources.",
        "Monitoring threshold: a failed browser QA check, accessibility report, or incorrect public record pauses release work for correction.",
        "Failure response: the maintainer can rollback to the last verified release and reset browser-local roadmap data.",
        "Second-order effects are reduced by stating that results do not decide eligibility or award funding.",
        "Image description: the attached desktop capture shows the state-first workflow and result layout.",
    ])
    intake = {
        "project_name": "RERC Community Explorer public usability release",
        "work_product": work_product,
        "work_type": "website",
        "intended_audience": "US communities, local governments, tribes, nonprofits, businesses, and residents",
        "client_locality": "United States and territories",
        "purpose": "Help people find public programs without overstating eligibility.",
        "required_outcome": "A clear, trustworthy, mobile-ready public explorer.",
        "applicable_standards": [
            "plain-language public communication",
            "responsive web usability",
            "transparent program boundaries",
            "privacy by design",
        ],
        "supporting_sources": ["Local Playwright QA PASS", "RERC catalog with official source links"],
        "prior_feedback": [
            "Roadmaps kept old selections after a community changed.",
            "Users needed clear stage controls and save feedback.",
        ],
        "known_constraints": [
            "Static website with browser-local roadmap data.",
            "Program status is not a legal eligibility decision.",
            "Catalog dates require periodic maintenance.",
        ],
        "review_criteria": [
            "Find remaining public-facing usability, trust, privacy, accessibility, or clarity risks.",
        ],
        "responsible_party": "RERC Explorer maintainer",
    }
    version = {
        "id": "rerc-public-usability-release",
        "project_id": "rerc-community-explorer",
        "number": 1,
        "content": work_product,
        "files": [
            {
                "name": "desktop.png",
                "media_type": "image/png",
                "content_base64": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            },
            {
                "name": "playwright_qa.json",
                "media_type": "application/json",
                "content": json.dumps(qa, indent=2),
            },
        ],
    }
    review = ReviewEngine(JUDGE_ROOT).run(intake, version)
    output_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
    summary = {
        "verdict": review["overall_verdict"],
        "can_proceed": review["can_proceed"],
        "red_team": review["red_team"]["verdict"],
        "faces": review["face_status"],
        "findings": review["correction_register"],
        "output": str(output_path),
    }
    print(json.dumps(summary, indent=2))
    return 0 if review["can_proceed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
