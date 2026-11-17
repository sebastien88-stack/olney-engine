# Security and privacy

## Report vulnerabilities privately

Do not open a public issue containing exploit details, credentials or personal
records. If enabled, use **Security → Advisories → Report a vulnerability** in
this repository to send a private report to the maintainer.

If that option is unavailable, the private channel has not yet been enabled.
Ask the maintainer to enable private vulnerability reporting without disclosing
the vulnerability itself. No security email or response deadline has been
designated; this document does not invent one.

Include the affected version, reproduction steps with synthetic inputs, impact
and suggested mitigation when available. Allow coordination before disclosure.
The maintainer evaluates reports for the current development branch; there is
no guaranteed support schedule for older releases.

## Protect personal information

The user SQLite database lives outside the source tree. Never upload it, private
chat logs, screenshots containing other people's birth details, or API keys to
issues, PRs or build artifacts. OpenAI/OpenRouter keys are held in session memory
or read from the process environment. They are not saved in the user database.
Chosen AI services receive messages and calculated context when the user sends
a chat request. Offline engine calculations do not require those services.

## Accidental exposure

If a real secret is exposed, revoke/rotate it with its provider promptly.
Removing a file in a new commit does not remove earlier history. Coordinate any
history rewrite with the owner; it must not happen automatically.
