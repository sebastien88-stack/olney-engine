# Data boundaries and demonstration inputs

The Historical Atlas is a planned independent dataset. It is not included in
this change, and no Atlas schema or migration is created. Publication requires
an explicit maintainer decision and provenance/license review of the actual data.

The desktop application starts with an empty user SQLite database. Its normal
path is outside the project. Tests use temporary databases and synthetic inputs.
`examples/demo_profile.json` is a clearly identified fictional documentation
example, not a real person's record and not a supported import format.

`data.json` is required card-calculation reference data, not the future Atlas or
a user profile database. `places.json` is a geographical lookup dataset. Their
license/provenance status is documented separately in LICENSING.md.

Do not add real private profiles, event participants, messages, API credentials
or personal exports to Git, fixtures or CI artifacts. Ignore rules are a guard,
not a substitute for reviewing staged files. Existing public screenshots were
provided by the owner; this does not authorize other people's private information.

Private Atlas work should live outside this repository. An ignored local
`atlas-private/` directory is available only as a convenience. Never use ignore
rules as proof that data was not previously committed; inspect Git history too.
