# RERC Community Explorer

Public GitHub Pages site for exploring funding, technical resources, and official community examples relevant to Recreation Economy *for* Rural Communities work.

Live site: <https://henkelpress.github.io/rerc-grant-finder/>

## Current Catalog

- 1,272 public records
- 659 funding options
- 137 guides, tools, data sources, training programs, and other resources
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


## Case Studies

The community-example layer includes only public text and links from official EPA, U.S. Climate Resilience Toolkit, and USDA Rural Development pages. Private records, local paths, administrative notes, and images are excluded. The 2026-07-18 automated check reached 271 of 303 unique pages directly. USDA Rural Development blocked automated access to 32 pages, so those links require manual review; no case-study link returned a hard failure.

## Meet RERC-e

RERC-e Local Grant-Writing Guide is an optional Windows app. It helps people review likely funding matches and turn project notes into a structured first draft. Local Gemma may select exact excerpts from supplied evidence; RERC-e verifies them and places them in a fixed outline. Raw model prose is not shown.

- Friendly Windows setup wizard
- No command-line setup for the person installing it
- Start Menu shortcut and optional desktop shortcut
- No account or API key required for local writing
- First use downloads a verified Google Gemma 3 1B model, about 0.81 GB
- Real Word `.docx` and Markdown export

[Download RERC-e for Windows](https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Setup.exe)

The current public installer is RERC-e 0.4.0. It passed installer QA and uses Google Gemma 3 1B. The installer is not code-signed, so Windows may show a safety notice. RERC-e 0.5.0 has passed source and local-generation QA but is not the public installer yet. RERC-e is a community-built tool. It is not an EPA grant program, does not decide eligibility, and does not submit applications.

The reviewed source and Timberwing Systems license are in `rercie/`. Model weights are not stored in this repository or installer.

## Release QA

- `python scripts/qa_release.py`
- `python scripts/qa_case_studies.py`
- `python scripts/check_case_sources.py`
- `node scripts/qa_public_site.cjs <site-url> <output-folder>`

## Automated Checks

The `Daily Grant and Resource Update Check` workflow checks every catalog source each day, compares available source signals such as status, redirects, ETag, last-modified date, and content length with the prior run, and uploads a review report. The `Daily Federal Opportunity Discovery` workflow searches the public Grants.gov API each day and uploads a review queue of posted and forecasted opportunities related to rural development, outdoor recreation, trails, tourism, community development, economic development, and technical assistance.

New opportunities, changed source signals, and status changes require human review before they enter the public catalog. The monitoring workflows do not publish unreviewed records.

## Publication Boundary

Do not add raw working files, source-audit tables, private records, private notes, email chains, private reference files, model weights, generated logs, PID files, or draft QA material to this public repository.
