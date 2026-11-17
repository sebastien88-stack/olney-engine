# Maintainer setup: review before enabling

This preparation does not change repository permissions, merge any PR, activate
rulesets, enable security settings or create a release.

## Protect main after the first CI run

1. In the repository, open **Settings → Rules → Rulesets → New branch ruleset**.
2. Name it `main-review-and-checks`, choose Active when ready and target `main`.
3. Require a pull request before merging, at least one approval, dismiss stale
   approvals on new commits and require approval from Code Owners.
4. Require conversations to be resolved.
5. Require status checks before merging and a branch up to date with main.
   Select **Windows Python 3.12 checks** after it has completed on this PR.
6. Block force pushes and branch deletion. Keep bypass permissions minimal;
   if you need a sole-maintainer bypass for your own PRs, choose it deliberately.
7. Review and save. Do not grant additional collaborators write/admin access
   merely to allow contributions: forks and PRs suffice.

CODEOWNERS requests the repository owner's review but does not enforce it by
itself. With code-owner review required, an outside contributor's approval is
not a substitute for the owner's review. Authors cannot approve their own PRs:
a sole maintainer may need an explicitly chosen bypass or another trusted owner.
Do not configure an impossible review gate accidentally.

If rulesets are unavailable, use **Settings → Branches → Add branch protection
rule**, pattern `main`, with the equivalent PR/review/status-check options.
The exact layout depends on GitHub's available account features.

## Confidential security reports

Enable **Settings → Advanced Security → Private vulnerability reporting**.
Then reporters can use **Security → Advisories → Report a vulnerability**.
SECURITY.md describes the conditional process and does not claim it is enabled.

Choose a separate confidential contact for conduct reports if desired. No email
address is invented or made public by this preparation.

## Resource-rights review before merge/release

- Confirm authorship and distribution rights of workbook-derived `data.json`.
- Review excerpts/paraphrases in `interpretation/` and decide content licenses.
- Verify original source and distribution rights of the recreated star artwork.
- Decide licenses for original logo, screenshots and project documentation.
- Reconcile any owner-confirmed grants in LICENSING.md before calling the whole
  distribution open source. Exclude or replace resources that cannot be cleared.
- Before another binary release, preserve Python/Tcl/Tk and all other runtime
  notices, and ship corresponding source matching the binary.

## Suggested first issues

1. Document Git Bash and PowerShell environment-variable setup: a small
   documentation-only task suitable for `good first issue`.
2. Add a narrowly scoped synthetic calendar-boundary regression test after
   agreeing the expected rule: `tests`, not automatically `good first issue`.
3. Review label wrapping in profile/event grids at smaller sizes: `ui`, with
   light/dark screenshots and a reproducible layout report.
4. Measure timeline recalculation time with synthetic inputs before proposing
   caching changes: `performance`.

Issues are invitations to discuss, not claims that these are confirmed bugs.
Useful labels: `bug`, `enhancement`, `documentation`, `tests`, `ui`,
`performance`, `good first issue`. This preparation can create these labels and
selected concrete issues; labels do not affect collaborator permissions.
