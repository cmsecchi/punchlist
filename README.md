# punchlist

A Claude Code plugin and a set of templates for a ticket-driven workflow: a person writes tickets
with testable "Done when" lines, GitHub Actions writes the code test-first, an independent reviewer
checks it, and the person merges.

Named after the construction punch list: the list an owner walks before accepting the work, where
every item must be done and checked.

Status: v0.2, early. Its first end-to-end rehearsal is in progress; expect changes.

## Install

In Claude Code:

```bash
claude plugin marketplace add cmsecchi/punchlist
```

```bash
claude plugin install punchlist@cmsecchi
```

Then set up each project repo as described in "What a project needs".

## What is in it

| Path | What it is | How a project uses it |
|---|---|---|
| `.claude-plugin/plugin.json` | The plugin: name and version | Enabled by the workflows |
| `.claude-plugin/marketplace.json` | Lets a repo install this plugin | Added as a marketplace |
| `skills/tdd/` | Writer skill: one Done-when line at a time, red then green | Loaded by the writer and fixer |
| `skills/review/` | Reviewer skill: three axes, Spec, Standards and Security, stance "refute" | Loaded by the reviewer |
| `dev-rules.md` | The developer rules | Copied verbatim into the project's `AGENTS.md` |
| `templates/issue.md` | The ticket shape | Copied to `.github/ISSUE_TEMPLATE/ticket.md` |
| `templates/build.yml` | Writer, then up to two review and fix rounds, triggered by the `go` label | Copied to `.github/workflows/` |
| `templates/review.yml` | The reviewer, read-only, called by `build.yml` | Copied to `.github/workflows/` |
| `templates/secrets.yml` | Secret scan (gitleaks) on every PR and push to `main` | Copied to `.github/workflows/` |
| `templates/screenshots.yml` | On PRs that change `frontend/`, runs `make screenshots` and posts up to three images in one PR comment; the PR's code never gets a write token or secrets | Copied to `.github/workflows/` (optional) |
| `templates/backup.yml` | Daily encrypted `pg_dump` of the production PostgreSQL, proved by restoring it into a throwaway database, kept 30 days as a workflow artifact | Copied to `.github/workflows/` (optional) |
| `templates/backup-restore.yml` | Manual recovery: decrypts a backup and restores it into an empty database; refuses one that has tables | Copied with `backup.yml` |

Copied files are never edited in the project: a change is made here, the version is bumped, and a
sync PR replaces the copy in each project.

## What a project needs

- An `AGENTS.md` with the project's own part (stack, commands, conventions) and the block from
  `dev-rules.md`, and a `CLAUDE.md` whose only line is `@AGENTS.md`. `AGENTS.md` is the shared
  convention many coding agents read; Claude Code reads it through the import.
- A `Makefile` with `setup`, `test`, `lint` and `dev`. The rules and workflows only call these.
- Its own `.github/workflows/ci.yml` (tests and lint on every PR; it depends on the stack).
- The labels `go`, `ready`, `prio` and `needs-you`.
- The secret `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`).
- The Claude GitHub App installed on the repo.
- A `main` ruleset: PR required, CI and the secret scan must pass, no force push, no bypass.
  Squash merge only.
- Dependabot alerts on (Settings, Advanced Security): known vulnerabilities in dependencies.
- Optional `make screenshots`: writes at most three PNG files to `screenshots/` (made-up data,
  never production). Used by `screenshots.yml`.
- Optional backups (`backup.yml`, `backup-restore.yml`): secrets `BACKUP_DATABASE_URL` (a
  read-only role on the production database) and `BACKUP_PASSPHRASE` (also kept in a password
  manager: without it the backups cannot be read), and the variable `BACKUP_PG_MAJOR` when the
  server is not PostgreSQL 16. `RESTORE_DATABASE_URL` is added only to recover.
- Optional `docs/security.md`: extra security rules for this app (e.g. a database with personal
  data). The reviewer checks them on top of its baseline.

## How a ticket flows

1. A ticket gets the `go` label.
2. `build.yml`: the writer reads the ticket, works one Done-when line at a time and opens a draft PR.
   What it finds outside the ticket goes in the PR's "Follow-ups" section (three at most); agents
   never open issues.
3. `review.yml` reviews it. If it asks for changes, a fixer addresses them and it reviews again,
   two fix rounds at most.
4. Approved: the PR is marked ready for review. Otherwise the ticket gets `needs-you`.
5. A person reads and merges.

## Not verified yet

Checked in the first rehearsal; if one fails, the fix lands here.

- The plugin installs from this public repo inside Actions.
- Claude Code in Actions reads `AGENTS.md` through the `@AGENTS.md` import in `CLAUDE.md`.
- Pinning: Actions installs the marketplace's current version, not a pinned one.
- The writer's PR, opened with the Claude app's token, starts `ci.yml`.
- GitHub emails the owner when a scheduled `backup.yml` run fails.
- The reviewer's verdict comes back through `structured_output`.

## Licence

MIT. The `tdd` and `review` skills are adapted from
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT); see `LICENSE`.
