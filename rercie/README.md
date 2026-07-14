# RERCie Local Grant-Writing Guide

RERCie Local Grant-Writing Guide is an optional app for the Recreation Economy *for* Rural Communities funding and resource explorer.

The Windows installer includes the RERCie app and the pinned `llama.cpp` runtime. The local Gemma writer does not require a command line, an account, or an API key. The Gemma model is downloaded only when the person selects **Download and start**.

## Install RERCie on Windows

1. Download `RERCie-Setup.exe` from the latest GitHub release.
2. Open the installer and follow the setup screens.
3. Keep the Start Menu shortcut. You can also choose a desktop shortcut.
4. Select **Meet RERCie** on the last screen.
5. Select **Download and start**. RERCie downloads the local model and checks it before opening.

The first model download is about 0.81 GB. RERCie checks the model before using it. Later starts use the model already on the computer.

When upgrading from version 0.3.1, setup removes the earlier local model folder. The next start downloads only Google Gemma.

No command line is needed. Open RERCie from the Start Menu. The launcher can open or stop the local tool.

## What RERCie Does

- Loads the current public RERC funding list.
- Accepts project notes and selected text files.
- Can look up a verified Census place or county profile. For American Samoa, Guam, the Northern Mariana Islands, and the U.S. Virgin Islands, it adds available territory-level Census context.
- Creates a first-draft grant narrative with clear fact-check markers.
- Exports a real Word `.docx` file or Markdown.
- Includes all 50 states, the District of Columbia, and five U.S. territories.

## Privacy

Gemma writing and files in `local_knowledge` stay on this computer. The public funding lookup and optional Census lookup use public websites. The Census Bureau requires a free API key for community facts; RERCie can read `CENSUS_API_KEY` from this computer or use a key pasted into the friendly lookup field for that session. The Census key is not sent to Gemma and is not saved by RERCie.

Do not add private files to a public copy of this project. Local reference files belong in `local_knowledge`.

## Human Review Required

RERCie is a community-built tool. It is not an EPA grant program. It does not decide final eligibility or submit an application. Before using a draft:

1. Open the official funding page.
2. Confirm the deadline, applicant rules, match, award size, and allowed work.
3. Replace every bracketed note with a checked local fact.
4. Have a person review the full application.

## Build the Installer: Developers Only

Most people should use RERCie-Setup.exe. The steps below are only for developers who are building the installer.

The source tree does not contain generated executables, the `llama.cpp` runtime, or model weights. `build_installer.ps1` runs the source smoke test, builds the hidden Python service with PyInstaller, compiles the native Windows launcher, verifies the pinned runtime archive, writes the integrity manifest, and creates `RERCie-Setup.exe` with Inno Setup.

```powershell
python -m pip install -r .\requirements-build.txt
.\build_installer.ps1 -AcceptRuntimeDownload
```

The public installer is not yet digitally signed. A production publisher should add a trusted Windows code-signing certificate before broad institutional deployment.

## Help

If RERCie does not open, start it again from the Start Menu. If an installed file fails its safety check, run the installer again. Report repeat problems at [henkelpress/rerc-grant-finder](https://github.com/henkelpress/rerc-grant-finder/issues).
