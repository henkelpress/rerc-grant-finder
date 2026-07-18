# RERC Community Explorer

Public GitHub Pages site for exploring funding, technical resources, and official community examples relevant to Recreation Economy *for* Rural Communities work.

Live site: <https://henkelpress.github.io/rerc-grant-finder/>

## Current Catalog

- 1,196 public records
- 659 funding options
- 61 guides, tools, data sources, training programs, and other resources
- 476 official federal community examples
- Coverage for all 50 states, the District of Columbia, Puerto Rico, American Samoa, Guam, the Northern Mariana Islands, and the U.S. Virgin Islands

People can name a community for the appendix, choose its state or territory, select All, Funding, Resources, or Case studies, answer a few project questions, and export the matched results as a real Word DOCX or CSV. The full Word appendix, Excel workbook, and CSV include all three content types and their official URLs.

## Public Site Files

- `index.html`
- `styles.css`
- `rercie.css`
- `app.js`
- `data.js`
- `case_studies.js`
- `assets/`
- `downloads/`


## Community Examples

The community-example layer includes only public text and links from official EPA, U.S. Climate Resilience Toolkit, and USDA Rural Development pages. Private records, local paths, administrative notes, and images are excluded.

## Meet RERCie

RERCie Local Grant-Writing Guide is an optional Windows app. It helps people review likely funding matches and turn project notes into a structured first draft. Local Gemma may select exact excerpts from supplied evidence; RERCie verifies them and places them in a fixed outline. Raw model prose is not shown.

- Friendly Windows setup wizard
- No command-line setup for the person installing it
- Start Menu shortcut and optional desktop shortcut
- No account or API key required for local writing
- First use downloads a verified Google Gemma 3 1B model, about 0.81 GB
- Real Word `.docx` and Markdown export

[Download RERCie for Windows](https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Setup.exe)

[SHA-256 checksum](https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Setup.exe.sha256) | [Release QA](https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Release-QA.json)

RERCie is a community-built tool. It is not an EPA grant program, does not decide eligibility, and does not submit applications. The installer is not yet digitally signed, so Windows may show a safety notice. Installer lifecycle testing ran on the build computer, not a separate clean Windows virtual machine. Package testing included a local Gemma draft; a later standalone retest could not run because the local service was not open. Download it only from this repository's release page.

The reviewed source is in `rercie/`. Model weights are not stored in this repository or installer.

## Release QA

- `python scripts/qa_release.py`
- `python scripts/qa_case_studies.py`
- `python scripts/check_case_sources.py`
- `node scripts/qa_public_site.cjs <site-url> <output-folder>`

## Automated Checks

The `Weekly Source Link Check` workflow checks the catalog maintenance links and uploads a source-health report. The `Monthly Federal Opportunity Discovery` workflow searches the public Grants.gov API and uploads a review queue of posted and forecasted opportunities related to rural development, outdoor recreation, trails, tourism, community development, economic development, and technical assistance.

New opportunities and status changes require human review before they enter the public catalog. The discovery workflow does not publish unreviewed records.

## Publication Boundary

Do not add raw working files, source-audit tables, private records, private notes, email chains, private reference files, model weights, generated logs, PID files, or draft QA material to this public repository.
