# RERC Funding and Resource Explorer

Public GitHub Pages site for the Recreation Economy for Rural Communities funding and resource catalog.

Live site: https://henkelpress.github.io/rerc-grant-finder/

## Current Release

- 726 public items
- 633 funding opportunities
- 93 guides, tools, data sources, training programs, and other resources
- Coverage for all 50 states, the District of Columbia, Puerto Rico, American Samoa, Guam, the Northern Mariana Islands, and the U.S. Virgin Islands

People can enter a community, choose Funding, Resources, or Both, answer a few project questions, and export the selected results as a Word-compatible appendix or CSV. The full Word appendix and Excel workbook are also available from the site.

## Public Site Files

- `index.html`
- `styles.css`
- `app.js`
- `data.js`
- `downloads/`

## Local Grant Writer

`grant-writer-master/` contains Grant-at-Arms, an optional local writing companion. It runs separately from the public website. It can use Ollama and Gemma on the user's computer or an OpenAI-compatible API key entered by the user.

## Automated Checks

The `Weekly Source Link Check` workflow checks every unique public link and uploads a source-health report. The `Monthly Federal Opportunity Discovery` workflow searches the public Grants.gov API and uploads a review queue of posted and forecasted opportunities related to rural development, outdoor recreation, trails, tourism, community development, economic development, and technical assistance.

New opportunities require human review before they enter the public catalog. The discovery workflow does not publish unreviewed records.

## Publication Boundary

Do not add raw working files, source-audit tables, private notes, email chains, private reference files, model weights, or draft QA material to this public repository.
