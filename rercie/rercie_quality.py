from __future__ import annotations

import re

import rercie_core as app


app.APP_VERSION = "0.3.2"
app.SYSTEM_PROMPT = """You are RERCie, a careful grant-writing assistant for rural communities.

Use only facts supplied by the user, the selected funding record, public data returned by the app, and local reference files. Do not infer goals, benefits, eligibility, deadlines, award amounts, match rules, partners, budgets, letters, or local statistics. Write a document, not a conversation. Begin with the project title. Do not use a greeting, preamble, quotation marks around the title, or a request for feedback. Use the exact requested Markdown headings. Mark missing local facts as [add local fact]. Mark every unconfirmed funding rule or source detail as [check official source]. A person must review the draft before submission.
"""

_compose_prompt = app.compose_prompt
_build_draft = app.build_draft


def compose_prompt(payload, public_profile, local_knowledge):
    prompt = _compose_prompt(payload, public_profile, local_knowledge)
    title = payload.get("projectTitle") or "[add project title]"
    return prompt + f"""

Formatting rules:
- Begin exactly with: # {title}
- Use these exact level-two headings: Fit Summary; Project Need; Proposed Work; Community Benefit; Work Plan; Budget and Match Notes; Source and Eligibility Checks; Missing Details.
- Do not add a greeting, preamble, closing, or request for feedback.
- Mark unsupported local statements [add local fact].
- Mark unconfirmed funding statements [check official source].
"""


def normalize_model_draft(draft: str, title: str) -> str:
    text = (draft or "").replace("\r\n", "\n").strip()
    sections = (
        "Fit Summary", "Project Need", "Proposed Work", "Community Benefit", "Work Plan",
        "Budget and Match Notes", "Source and Eligibility Checks", "Missing Details",
    )
    for section in sections:
        text = re.sub(rf"(?im)^\s*\*\*{re.escape(section)}:?\*\*\s*$", f"## {section}", text)
        text = re.sub(rf"(?im)^\s*{re.escape(section)}:\s*$", f"## {section}", text)

    first_heading = re.search(r"(?m)^#{1,3}\s+", text)
    if first_heading and first_heading.start() > 0:
        text = text[first_heading.start():]
    if not re.match(r"(?m)^#\s+", text):
        text = f"# {title or '[add project title]'}\n\n{text}"
    if "[check official source]" not in text.lower():
        text += "\n\n## Required Official-Source Checks\n\n- [check official source] Confirm applicant eligibility.\n- [check official source] Confirm the current deadline, award size, match, allowed work, and required attachments."
    if "[add local fact]" not in text.lower():
        text += "\n\n- [add local fact] Replace any unverified local claim with a checked community fact."
    return text.strip()


def build_draft(payload):
    result = _build_draft(payload)
    if str(payload.get("provider") or "local").lower() in {"local", "api"} and not result.get("warnings"):
        result["draft"] = normalize_model_draft(result.get("draft", ""), str(payload.get("projectTitle") or "Grant Draft"))
    return result


app.compose_prompt = compose_prompt
app.build_draft = build_draft


if __name__ == "__main__":
    raise SystemExit(app.main())
