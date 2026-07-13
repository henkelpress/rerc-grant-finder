# RERC Funding and Resource Finder

Public GitHub Pages site for the Recreation Economy *for* Rural Communities funding and resource catalog.

Live site: <https://henkelpress.github.io/rerc-grant-finder/>

## Current Catalog

- 718 public items
- 653 funding options
- 65 guides, tools, data sources, training programs, and other resources
- Coverage for all 50 states, the District of Columbia, Puerto Rico, American Samoa, Guam, the Northern Mariana Islands, and the U.S. Virgin Islands

People can name a community for the appendix, choose its state or territory, select Funding, Resources, or Both, answer a few project questions, and export the matched results as a real Word DOCX or CSV. The full Word appendix and Excel workbook are also available from the site.

## Public Site Files

- `index.html`
- `styles.css`
- `grant-at-arms.css`
- `app.js`
- `data.js`
- `downloads/`

## Local Grant Writer

Grant-at-Arms is an optional Windows writing companion. It runs separately from the public site with a local Gemma 3 1B model through `llama.cpp`.

- No separate Python or Ollama installation
- Retrieves Microsoft's signed x64 runtime installer only if Windows is missing the standard runtime
- No account or API key required for local writing
- One start shortcut after extraction
- First run downloads the verified local model, about 806 MB
- Real Word `.docx` and Markdown export

[Download Grant-at-Arms for Windows](https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/grant-at-arms-local-writer.zip)

The reviewed source is in `grant-writer-master/`. Model weights are not stored in this repository or release ZIP.

## Automated Checks

The `Weekly Source Link Check` workflow checks every unique public link and uploads a source-health report. The `Monthly Federal Opportunity Discovery` workflow searches the public Grants.gov API and uploads a review queue of posted and forecasted opportunities related to rural development, outdoor recreation, trails, tourism, community development, economic development, and technical assistance.

New opportunities require human review before they enter the public catalog. The discovery workflow does not publish unreviewed records.

## Publication Boundary

Do not add raw working files, source-audit tables, private notes, email chains, private reference files, model weights, generated logs, PID files, or draft QA material to this public repository.
