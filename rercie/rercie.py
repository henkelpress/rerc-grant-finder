from __future__ import annotations

import re

import rercie_quality as quality


app = quality.app
app.APP_VERSION = "0.3.4"
_build_draft = app.build_draft


def normalize_headings(text: str) -> str:
    sections = (
        "Fit Summary", "Project Need", "Community Context", "Proposed Work", "Community Benefit",
        "Work Plan", "Budget and Match Notes", "Source and Eligibility Checks", "Missing Details",
    )
    normalized = text
    for section in sections:
        pattern = rf"(?im)^\s*\*\*{re.escape(section)}:?\*\*\s*(.*)$"
        normalized = re.sub(pattern, lambda match: f"## {section}\n\n{match.group(1).strip()}".rstrip(), normalized)
        normalized = re.sub(
            rf"(?im)^\s*{re.escape(section)}:\s*(.*)$",
            lambda match: f"## {section}\n\n{match.group(1).strip()}".rstrip(),
            normalized,
        )
    return normalized


def replace_section(text: str, heading: str, body: str) -> str:
    block = f"## {heading}\n\n{body.strip()}\n\n"
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n.*?(?=^##\s+|\Z)"
    if re.search(pattern, text):
        return re.sub(pattern, block, text, count=1)
    insert_before = re.search(r"(?m)^## Proposed Work\s*$", text) if heading == "Community Context" else None
    if insert_before:
        return text[:insert_before.start()].rstrip() + "\n\n" + block + text[insert_before.start():]
    return text.rstrip() + "\n\n" + block.rstrip()


def append_to_section(text: str, heading: str, notes: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n.*?(?=^##\s+|\Z)"
    match = re.search(pattern, text)
    if not match:
        return text.rstrip() + f"\n\n## {heading}\n\n{notes.strip()}"
    block = match.group(0).rstrip() + "\n\n" + notes.strip() + "\n\n"
    return text[:match.start()] + block + text[match.end():]


def section_body(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)", text)
    return match.group(1).strip() if match else ""


def apply_evidence_controls(text: str, payload, public_profile) -> str:
    guarded = normalize_headings(text)
    evidence_draft = app.deterministic_scaffold(payload, public_profile)
    for heading in (
        "Fit Summary", "Project Need", "Community Benefit", "Budget and Match Notes",
        "Source and Eligibility Checks", "Missing Details",
    ):
        guarded = replace_section(guarded, heading, section_body(evidence_draft, heading))
    if public_profile:
        guarded = replace_section(guarded, "Community Context", app.format_public_profile(public_profile))
    elif not re.search(r"(?m)^## Community Context\s*$", guarded):
        guarded = replace_section(
            guarded,
            "Community Context",
            "[add local fact] Add checked community facts that explain the need and cite their source.",
        )

    source_checks = (
        "- [check official source] Confirm eligible applicants, locations, work, and costs.\n"
        "- [check official source] Confirm the current deadline, award range, match, and required attachments."
    )
    source_match = re.search(r"(?ms)^## Source and Eligibility Checks\s*\n(.*?)(?=^##\s+|\Z)", guarded)
    if not source_match or "[check official source]" not in source_match.group(1).lower():
        guarded = append_to_section(guarded, "Source and Eligibility Checks", source_checks)

    missing_match = re.search(r"(?ms)^## Missing Details\s*\n(.*?)(?=^##\s+|\Z)", guarded)
    if not missing_match or "[add local fact]" not in missing_match.group(1).lower():
        guarded = append_to_section(
            guarded,
            "Missing Details",
            "- [add local fact] Add any missing local evidence, budget details, partners, schedule, and expected results.",
        )
    return re.sub(r"\n{3,}", "\n\n", guarded).strip()


def build_draft(payload):
    result = _build_draft(payload)
    provider = str(payload.get("provider") or "local").lower()
    if provider == "local" and not result.get("warnings"):
        public_profile = result.get("publicProfile") or {}
        issues = app.grounding_issues(result.get("draft", ""), payload, public_profile)
        if issues:
            result["draft"] = app.deterministic_scaffold(payload, public_profile)
            result["safetyNotice"] = "RERCie removed details that were not supported by the project notes or verified public facts."
            result["groundingIssues"] = issues
        else:
            result["draft"] = apply_evidence_controls(
                result.get("draft", ""),
                payload,
                public_profile,
            )
    return result


app.build_draft = build_draft


if __name__ == "__main__":
    raise SystemExit(app.main())
