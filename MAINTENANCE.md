# Maintaining the RERC Community Explorer

This site uses a state-or-territory starting point. It does not claim to determine local eligibility. Program rules and service areas remain controlling.

## Routine catalog edits

Edit the matching record in `data.js`. Keep these fields current and public-facing:

- `status`: plain-language current state, such as `Open when checked`, `Recurring`, `Cycle closed`, or `Available`.
- `deadline_or_availability`: the next known deadline; otherwise use `Rolling`, `Ongoing`, or a clear next-cycle note.
- `last_checked`: review date in `YYYY-MM-DD` format.
- `eligible_users`: the public `Who` statement shown on each card.
- `summary`: a short factual description.
- `source_url`: the current official program website.

Never paste email chains, staff notes, private paths, API keys, or unreviewed claims into public records.

## Regional programs

A record with `geography: "Multi-State"` must also have a reviewed entry in `maintenance/multistate_coverage.json` containing:

- `covered_states`: exact names from the 56 supported states, D.C., and U.S. territories;
- `coverage_note`: important county, coastal-zone, service-territory, or customer limits;
- `coverage_source_url`: an official page supporting the service area.

The site fails closed: a `Multi-State` record without explicit coverage appears for no state.

After editing the manifest, run:

```powershell
python scripts/sync_multistate_coverage.py --write
python scripts/qa_geography_coverage.py
```

## Match ranking and filters

Edit `site-config.js` to change:

- public applicant, topic, or project-stage choices;
- High, Medium, and Starting Point thresholds;
- documented scoring weights.

Match levels only rank the programs already allowed by geography. They do not determine eligibility. Keep that explanation visible whenever ranking rules change.

## Rebuild and review

Run these checks before publication:

```powershell
python scripts/sync_multistate_coverage.py
python scripts/qa_geography_coverage.py
python scripts/qa_funding_deadlines.py
python scripts/qa_release.py
node scripts/qa_public_site.cjs http://127.0.0.1:8877/ browser-qa
```

The full Word, Excel, and CSV package is built with:

```powershell
python scripts/build_full_public_package.py
```

The package report binds files to the current Git source commit. Commit reviewed source changes before the final package build, then commit the generated downloads and report.

## Daily monitoring

GitHub Actions checks source health and discovers federal opportunities each day. Those jobs create review evidence only. A person must verify and approve any public catalog change.