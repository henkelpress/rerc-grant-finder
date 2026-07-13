from __future__ import annotations

import re

import grant_at_arms_quality as quality


app = quality.app
app.APP_VERSION = "0.2.3"
_build_draft = app.build_draft


def normalize_headings(text: str) -> str:
    sections = (
        "Fit Summary", "Project Need", "Proposed Work", "Community Benefit", "Work Plan",
        "Budget and Match Notes", "Source and Eligibility Checks", "Missing Details",
        "Required Official-Source Checks",
    )
    normalized = text
    for section in sections:
        pattern = rf"(?im)^\s*\*\*{re.escape(section)}:?\*\*\s*(.*)$"
        normalized = re.sub(pattern, lambda match: f"## {section}\n\n{match.group(1).strip()}".rstrip(), normalized)
        normalized = re.sub(rf"(?im)^\s*{re.escape(section)}:\s*(.*)$", lambda match: f"## {section}\n\n{match.group(1).strip()}".rstrip(), normalized)
    return normalized


def replace_section(text: str, heading: str, body: str) -> str:
    block = f"## {heading}\n\n{body.strip()}\n\n"
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n.*?(?=^##\s+|\Z)"
    if re.search(pattern, text):
        return re.sub(pattern, block, text, count=1)
    return text.rstrip() + "\n\n" + block.rstrip()


def apply_evidence_controls(text: str, payload) -> str:
    title = str(payload.get("projectTitle") or "[add project title]")
    community = str(payload.get("community") or "[add community]")
    state = str(payload.get("state") or "[add state or territory]")
    project_summary = str(payload.get("projectSummary") or "[add project summary]")
    selected_grant = str(payload.get("selectedGrant") or "[select a funding source]")[:10000]
    match_capacity = str(payload.get("matchCapacity") or "[add match and capacity facts]")
    source_notes = str(payload.get("sourceNotes") or "[add the official source link and current details]")

    guarded = normalize_headings(text)
    guarded = replace_section(
        guarded,
        "Fit Summary",
        f"{title} may fit the selected funding source. [check official source] Confirm that the applicant, proposed work, location, costs, and schedule meet the current rules.\n\nSelected funding record:\n\n{selected_grant}",
    )
    guarded = replace_section(
        guarded,
        "Project Need",
        f"{community}, {state}, is seeking support for this stated need:\n\n{project_summary}\n\n[add local fact] Add checked local evidence that shows the size, location, and effect of this need.",
    )
    guarded = replace_section(
        guarded,
        "Budget and Match Notes",
        f"{match_capacity}\n\n[check official source] Confirm allowed costs, award size, match rules, and documentation before building the final budget.",
    )
    guarded = replace_section(
        guarded,
        "Source and Eligibility Checks",
        f"{source_notes}\n\n- [check official source] Confirm eligible applicants and locations.\n- [check official source] Confirm eligible work and costs.\n- [check official source] Confirm the current deadline, award size, match, and required attachments.",
    )
    guarded = replace_section(
        guarded,
        "Missing Details",
        "- [add local fact] Applicant legal name and project location.\n- [add local fact] Checked need data and expected results.\n- [add local fact] Total budget, committed match, staff, and partners.\n- [check official source] Current deadline and application requirements.",
    )
    if re.search(r"(?m)^## Community Benefit\s*$", guarded):
        guarded = guarded.replace(
            "## Community Benefit\n",
            "## Community Benefit\n\n[add local fact] Keep only benefits the community can support with its plan, records, or partner commitments.\n",
            1,
        )
    return re.sub(r"\n{3,}", "\n\n", guarded).strip()


def build_draft(payload):
    result = _build_draft(payload)
    provider = str(payload.get("provider") or "local").lower()
    if provider in {"local", "api"} and not result.get("warnings"):
        result["draft"] = apply_evidence_controls(result.get("draft", ""), payload)
    return result


app.build_draft = build_draft


if __name__ == "__main__":
    raise SystemExit(app.main())
