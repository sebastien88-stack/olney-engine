# Contributing to Olney Engine

Thank you for helping improve Olney. The maintainer reviews all contributions
and decides which changes fit the project. Submission does not guarantee acceptance.

## Start a discussion

Use a bug report for reproducible problems and a feature request for proposals.
Discuss substantial features, new dependencies, calculation-rule changes and
large UI changes in an issue **before** implementation. Provide synthetic
examples; never attach a personal database, API key or unredacted chat history.

## Set up and create a branch

1. Fork the repository on GitHub.
2. Clone your fork and follow the Python 3.12/Tcl-Tk setup in [English README](README.en.md#run-from-source).
3. Install test dependencies with `python -m pip install -r requirements-dev.txt`.
4. Add upstream and create a focused branch:

```bash
git remote add upstream https://github.com/sebastien88-stack/olney-engine.git
git fetch upstream
git switch -c fix/short-description upstream/main
```

Use `feat/`, `fix/`, `docs/` or `test/` followed by a short descriptive name.
Make small commits with a clear verb and purpose. Do not force-push shared main.

## Code conventions

Follow neighboring code, four-space Python indentation, `snake_case` names for
functions/modules and `PascalCase` for classes. Keep calculation and interpretation
separate. Engine results are authoritative: never replace them with LLM guesses.
Preserve validated series and calendar rules unless a documented correction is
agreed. Keep Tk widget operations on the UI thread; use the existing job helpers
for expensive work. Do not introduce network access into offline calculations.

UI strings are currently French; contributor docs are English. Include provenance
for interpretive claims and confirm rights before contributing data, text or images.
The Atlas is future work; do not commit historical datasets or migrations here.

## Validate

From the repository root:

```bash
python -m pytest tests -q
python tools/check_python.py
python tools/validate_interpretation.py
python tools/audit_public_repository.py
```

Pytest includes real-Tk startup, card-navigation and chat-opening journeys. Run
`python -m pytest tests -q -m ui` on Windows with Tcl/Tk to isolate them, or use
`-m "not ui"` for the other tests. Each journey runs in a separate process with
a temporary database and a 90-second timeout; it makes no AI request.
CI runs both **Windows Python 3.12 checks** and **Windows Tk UI journeys**.

Application versions derive from the root `version.py`; do not hardcode a copy
in runtime code or Windows metadata. Documentation and release notes are updated
separately when publishing.

For UI changes, launch `python app.py`, inspect light/dark modes at normal and
maximized sizes, and also run `python tools/ui_startup_smoke.py` on Windows with Tk.
Add meaningful regression tests for behavior changes. Docs-only changes need
link/content checks, not new tests. Never use real API keys in CI.

## Open a pull request

```bash
git add path/to/changed-file
git commit -m "Describe the change"
git push -u origin fix/short-description
```

Open a PR from your branch to upstream `main`. Explain the resulting behavior,
link the issue, list checks and compatibility changes, and attach screenshots
for visual changes. Remove identifying details from new screenshots. Respond to
review comments and keep unrelated changes separate. The maintainer gives final
approval and merges; contributors cannot directly publish or merge changes.

## Licensing and conduct

Your original code contribution is submitted under GPL-3.0-only. You retain
copyright. Do not submit code or assets you cannot license appropriately.
Resource exceptions are listed in [LICENSING.md](LICENSING.md).
Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report security issues through
the process in [SECURITY.md](SECURITY.md), not a public bug report.
