# RERC Funding and Resource Explorer

Public GitHub Pages site for the Recreation Economy *for* Rural Communities funding and resource catalog.

Live site: <https://henkelpress.github.io/rerc-grant-finder/>

## Current Catalog

- 720 public items
- 655 funding options
- 65 guides, tools, data sources, training programs, and other resources
- Coverage for all 50 states, the District of Columbia, Puerto Rico, American Samoa, Guam, the Northern Mariana Islands, and the U.S. Virgin Islands

People can name a community for the appendix, choose its state or territory, select Funding, Resources, or Both, answer a few project questions, and export the matched results as a real Word DOCX or CSV. The full Word appendix and Excel workbook are also available from the site.

## Public Site Files

- `index.html`
- `styles.css`
- `rercie.css`
- `app.js`
- `data.js`
- `assets/`
- `downloads/`

## Meet RERCie

RERCie Local Grant-Writing Guide is an optional Windows app. It helps people review likely funding matches and turn project notes into a first draft.

- Friendly Windows setup wizard
- No command-line setup for the person installing it
- Start Menu shortcut and optional desktop shortcut
- No account or API key required for local writing
- First use downloads a verified Qwen 2.5 1.5B model, about 1.12 GB
- Real Word `.docx` and Markdown export

[Download RERCie for Windows](https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Setup.exe)

RERCie is a community-built tool. It is not an EPA grant program, does not decide eligibility, and does not submit applications. The installer is not yet digitally signed, so Windows may show a safety notice. Download it only from this repository's release page.

The reviewed source is in `rercie/`. Model weights are not stored in this repository or installer.

## Automated Checks

The `Weekly Source Link Check` workflow checks the catalog maintenance links and uploads a source-health report. The `Monthly Federal Opportunity Discovery` workflow searches the public Grants.gov API and uploads a review queue of posted and forecasted opportunities related to rural development, outdoor recreation, trails, tourism, community development, economic development, and technical assistance.

New opportunities and status changes require human review before they enter the public catalog. The discovery workflow does not publish unreviewed records.

## Publication Boundary

Do not add raw working files, source-audit tables, private notes, email chains, private reference files, model weights, generated logs, PID files, or draft QA material to this public repository.