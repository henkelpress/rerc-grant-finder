# Grant-at-Arms Local Grant Writer

Grant-at-Arms is the optional local writing companion for the EPA RERC Grant Finder.

It is separate from the public website. The website helps people find likely grant matches. This local tool helps draft grant narratives from the selected grant, project notes, public data, and local reference files.

## What It Does

1. Runs a private web interface at `http://127.0.0.1:8789`.
2. Uses a local Ollama model by default, such as `gemma3:4b`.
3. Can use an OpenAI-compatible API endpoint if the user enters an API key.
4. Reads selected text files in the browser before drafting.
5. Reads local reference files from `local_knowledge\`.
6. Pulls a basic Census place profile when a community and state are provided.
7. Exports draft text as Markdown or Word-readable `.doc`.

## Setup On Windows

Run these commands from this folder:

```powershell
.\install.ps1
.\run.ps1
```

Then open:

```text
http://127.0.0.1:8789
```

## Model Choice

The default local model is:

```text
gemma3:4b
```

To use a smaller model:

```powershell
$env:GRANT_AT_ARMS_MODEL = "gemma3:1b"
.\run.ps1
```

To use a larger model:

```powershell
$env:GRANT_AT_ARMS_MODEL = "gemma3:12b"
.\run.ps1
```

Do not add model weights to this repository. `install.ps1` asks Ollama to download the model on the user's machine.

## Add Local Reference Material

Put plain text reference files here:

```text
local_knowledge\
```

Supported file types:

1. `.md`
2. `.txt`
3. `.csv`
4. `.json`

Do not put private files in a public fork of this repository. The local app reads files from `local_knowledge\` only when it runs on the user's computer.

## Drafting Rules

Grant-at-Arms is a drafting tool. It does not submit applications. It does not make final eligibility decisions.

Before using any draft in a real application:

1. Check the current grant source.
2. Confirm the deadline.
3. Confirm applicant eligibility.
4. Confirm match rules.
5. Replace placeholders with local facts.
6. Have a person review the final application.

