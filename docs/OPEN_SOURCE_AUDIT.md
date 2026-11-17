# Open-source preparation audit — 2026-11-17

## Status of this report

This is the historical record of the initial open-source preparation, based on
`1808f72`. Counts, branch descriptions and the 1.8.6 references in that record
belong to that stage; they do not describe today's downloadable version.

As of the documentation update on 2026-11-17:

- The latest Windows release is 1.8.9, tagged at `5856193`.
- Local sources and GitHub `main` matched at `cd885bf` before this documentation
  update. Development changes after the tag are not in the 1.8.9 downloads.
- `version.py` is now the sole application version source; the declared version
  remains 1.8.9 pending a future release.
- At `cd885bf`, compilation passed for 85 tracked Python files, all 172 pytest
  tests passed, and interpretation validation passed.
- CI now has two blocking Windows/Python 3.12 jobs: **Windows Python 3.12 checks**
  and **Windows Tk UI journeys**. The latter covers startup, card navigation and
  opening the chat workspace, with isolated databases and subprocess timeouts.
  It was promoted only after a successful nonblocking Windows run.
- Both jobs passed: https://github.com/sebastien88-stack/olney-engine/actions/runs/44166995752
- French is the main README, with an English translation linked at the top.
- Further extraction of `app.py` is deferred because remaining views depend on
  application globals; no behavioral refactor was performed.

This update does not repeat the original credential scan, change license
findings, activate branch protections or publish a binary. Rights questions
remain pending in LICENSING.md.

## Initial preparation record

Scope: existing Olney Engine repository, preparation branch based on `1808f72`.
No engine refactor, no Atlas import, no new binary release and no history rewrite.

## Architecture and dependencies

Python 3.12/Tkinter/ttk desktop app, SQLite local storage and urllib HTTP calls.
The calculation engine uses validated `data.json` series. Interpretations, cycle
readings, relationship context, persistence and UI are separate modules, though
`app.py` remains the large application coordinator. Runtime requirements contain
no pip dependencies. `tzdata` and a GeoNames-derived place index are bundled.
Pytest is a development dependency; PyInstaller and Inno Setup are packaging tools.

The app starts with an empty database outside the repository. Tests create
temporary databases. The future Historical Atlas is absent; the new example
profile is explicitly synthetic and does not change any import format.

## Credential and personal-data review

Baseline: 746 tracked files; all four pre-preparation commits and 481 unique
historical blobs were scanned with tools/audit_public_repository.py. No matching
credential patterns or tracked database/private-key/.env paths were found.
The scan was repeated for the prepared working tree and reachable history.

Patterns cover provider-key shapes, GitHub tokens, PEM private-key headers,
AWS access-key IDs and suspicious literal credential assignments. Matches are
reported by path/rule/blob only; values are never printed. This is a heuristic,
not a guarantee that every form of secret is detected.

No real secret was identified, so no revocation or history rewrite was performed.
Existing screenshots show the owner's name and birth details, explicitly
provided for publication. Existing tests also use some owner-supplied birth
examples. The repository is therefore **not anonymous**, even though no private
profile database is tracked. New examples are fictional; do not infer consent
to publish other people's records. Existing public history is left unchanged.

Ignored build artifacts include a temporary smoke-test database under `build/`;
that directory is not tracked or uploaded. Environments, caches, releases and
downloaded installers are excluded. New ignore rules cover private Atlas work,
personal exports, SQLite sidecars and private-key files. Ignore rules do not
erase earlier commits.

## Licensing findings

- Original source code: owner-authorized GPL-3.0-only proposal, full license in
  LICENSE. LICENSE.txt's previous blanket proprietary grant is removed on this
  branch; resource exclusions are explicit in LICENSING.md.
- Bundled tzdata package: Apache-2.0 notice exists. Apache-2.0 is compatible with
  GPLv3; preserve upstream notices. [Apache compatibility statement](https://apache.org/licenses/GPL-compatibility.html).
- IANA timezone data: public-domain dataset according to
  [IANA](https://www.iana.org/time-zones/tz-link). Preserve source notices.
- places.json: offline transformation of GeoNames cities5000, declared CC BY 4.0
  with attribution. It is separate data, not relicensed as GPL code. Retain the
  license URL, source and transformation description. [GeoNames](https://www.geonames.org/export/).
- Python 3.12 and Tcl/Tk: distributed runtime components retain their own
  notices; no obvious code-license incompatibility identified for the modern
  Python/Tk toolchain. Exact future binary contents still need a packaging
  notice review. [Python licensing history](https://docs.python.org/3/license.html).
- PyInstaller: build tool, with a bootloader distribution exception; Inno Setup:
  external compiler with its own use terms. This PR does not relicense either
  tool or produce a binary. [PyInstaller license](https://pyinstaller.org/en/stable/license.html).
- Workbook-derived canonical series, book-derived corpus and recreated artwork:
  **redistribution rights unresolved**. Provenance references books and a
  workbook but does not establish a grant. No blanket GPL claim is made for them.

Conclusion: no confirmed GPLv3-incompatible first-party runtime code dependency
was found, but the **whole application's resource-rights clearance is pending**.
Keep this preparation in draft until the owner resolves the checklist in
LICENSING.md / docs/GITHUB_SETUP.md. A code license cannot grant third-party rights.

## Validation

- 163 pytest tests pass, using mocked APIs and local synthetic/fixture data.
- Interpretation validation passes: 52 cards/polarities/profiles, elements,
  stable fixed cards across 90 tables, hierarchy, context schemas and cycles.
- Python compilation passes for tracked Python files, including new tooling.
- New isolated UI startup smoke test passes with the real Tk interface.
- Existing asynchronous UI smoke passes after replacing its stale pre-parchment
  color expectation with the current shared palette. Production code unchanged.
- Calculation modules, data.json and interpretation corpus have no changes in
  this branch; runtime and release version remain 1.8.6.
- README local links/captures, JSON example, Git whitespace and YAML/workflow
  structure are checked before PR submission; GitHub's first run will confirm
  runner behavior and status-check availability.

GitHub subsequently confirmed the complete workflow succeeds on the integrated
revision `1042da1`, for both push and pull_request events:
https://github.com/sebastien88-stack/olney-engine/actions/runs/44090392879
The first branch revision's workflow also passed. The later branding changes
made by the owner on main were merged into the preparation branch and preserved
in English and French; the two uploaded branding images remain resource exceptions.

## GitHub actions and remaining owner decisions

The workflow uses a single Windows/Python 3.12 job with read-only contents
permission, no stored checkout credentials, a 15-minute limit and cancellation
of superseded runs. It runs tests, compilation, corpus/credential checks and
isolated startup. It does not access secrets, publish or install the application.

PR and issue forms, CODEOWNERS and contribution/conduct policies are prepared.
Branch protections, private vulnerability reporting, collaborator permissions
and publishing settings are not changed. Activate settings using
docs/GITHUB_SETUP.md only after reviewing the PR and its first CI run.

The conduct policy deliberately leaves its confidential contact undesignated;
the owner can choose one. The English README links to the preserved French
illustrated version. Detailed historical notes keep their old-release context.

## Review links

- Draft PR: https://github.com/sebastien88-stack/olney-engine/pull/1
- Small documentation task: https://github.com/sebastien88-stack/olney-engine/issues/2
- Resource-rights checklist: https://github.com/sebastien88-stack/olney-engine/issues/3
- Added labels: tests, ui, performance; existing standard labels are reused.
