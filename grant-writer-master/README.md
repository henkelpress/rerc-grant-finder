# Grant-at-Arms Local Grant Writer

Grant-at-Arms is an optional writing companion for the Recreation Economy *for* Rural Communities funding and resource finder.

The downloaded Windows release uses the Gemma 3 1B model through `llama.cpp`. It does not require a separate Python or Ollama installation, an account, or an API key.

## Start the downloaded release

1. Extract the full ZIP.
2. Double-click `Start-Grant-at-Arms.cmd`.
3. Read the first-run notice and type `Y` to download Gemma.
4. The tool opens at `http://127.0.0.1:8789`.

The first run downloads the local model, about 806 MB. If Windows is missing the standard Microsoft Visual C++ runtime, the launcher verifies and runs Microsoft's official installer first. Later runs use the copy in the `models` folder.

Double-click `Stop-Grant-at-Arms.cmd` when you are finished.

## What It Does

- Loads the current public RERC funding list.
- Accepts project notes and selected text files.
- Can look up a basic Census place profile.
- Creates a first-draft grant narrative with clear fact-check markers.
- Exports a real Word `.docx` file or Markdown.
- Includes all 50 states, the District of Columbia, and five U.S. territories.

## Privacy

Local Gemma writing stays on this computer. The public funding lookup and optional Census lookup use public websites. Online API mode sends typed or uploaded project text, selected funding details, and any public Census profile to the API provider selected by the user. It does not read or send files from `local_knowledge`. API keys are used for one request and are not saved by Grant-at-Arms.

Do not add private files to a public copy of this project. Local reference files belong in `local_knowledge`.

## Human Review Required

Grant-at-Arms does not decide final eligibility or submit an application. Before using a draft:

1. Open the official funding page.
2. Confirm the deadline, applicant rules, match, award size, and allowed work.
3. Replace every bracketed note with a checked local fact.
4. Have a person review the full application.

## Source Checkout

The source tree does not contain the generated EXE or the `llama.cpp` runtime. The files under `packaging\` are copied to the root of the downloadable release ZIP during the release build. `build_portable.ps1` builds the EXE from the published module names, checks the pinned runtime archive, adds the complete Python license notice, creates the file-integrity manifest, and builds the release ZIP.

Run the source smoke test with Python:

```powershell
python .\grant_at_arms.py --smoke
```

Build the portable package from Windows PowerShell with Python 3.11 or newer:

```powershell
python -m pip install -r .\requirements-build.txt
.\build_portable.ps1 -AcceptRuntimeDownload
```

The release does not redistribute Microsoft runtime DLLs. On a computer where they are missing, the launcher retrieves the current signed x64 installer directly from Microsoft.

## Troubleshooting

Logs are stored in `runtime\logs`.

Run this check in PowerShell from the extracted release folder:

```powershell
.\Start-Grant-at-Arms.ps1 -DryRun
```

The public source and build scripts are available at [henkelpress/rerc-grant-finder](https://github.com/henkelpress/rerc-grant-finder).
