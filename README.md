# EPA RERC Grant Finder

Public GitHub Pages bundle for the RERC grant finder.

This repository publishes the static public website and the optional local writing companion:

1. `index.html`
2. `styles.css`
3. `app.js`
4. `data.js`
5. `grant-writer-master\`

Do not add raw working files, source audit tables, private notes, private reference files, model weights, or draft QA material to this public repository.

## Publish

1. Push this folder to a GitHub repository.
2. Enable GitHub Pages with GitHub Actions as the source.
3. Run the `Deploy GitHub Pages` workflow.

## Local Grant Writer

The `grant-writer-master\` folder contains Grant-at-Arms, an optional local companion app. It can use Ollama and Gemma on the user computer, or an OpenAI-compatible API key entered by the user.

## Check Source Links

The `Weekly Source Link Check` workflow runs every Monday at 10:17 UTC. It checks the public source links in `data.js` and uploads a report artifact.

New grants should enter a private review queue first. Do not auto-add new grants to the public site without human review.
