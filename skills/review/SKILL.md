---
name: review
description: Review a pull request on three separate axes, Spec (does it do what the ticket's Done-when lines ask?), Standards (does it follow the repo's rules?) and Security (does it open a hole?), trying to refute it rather than confirm it. Use when asked to review a PR, a branch or a diff against its ticket.
---

# Three-axis review

Adapted from Matt Pocock's `code-review` skill (MIT, see LICENSE). One pass, no sub-agents.

Stance: **refute, not confirm.** Assume the PR is wrong until the diff shows otherwise. Approval
is earned by evidence in the diff and the tests, never by the PR description, which the writer
wrote.

## Inputs

- The ticket: the issue named in `Closes #N`. Its Done-when lines are the spec; its Risk areas
  say whether personal data or paid APIs are in play.
- The diff against the base branch (`git diff origin/main...HEAD`, or `gh pr diff`).
- The standards: the repo's `AGENTS.md` (developer rules included) and any `CONTRIBUTING.md` or
  style document it points to.
- The repo's own security rules, if it has them: `docs/security.md`. They add to the baseline
  below, never replace it.

## Axis 1: Spec

For each Done-when line, answer:

- Is there a test that proves it? Quote the test name. A test that cannot fail, asserts a
  recomputed value, or tests something else does not count.
- Does the code actually do it, including the obvious edge the line implies?

Then list:

- **Missing or partial**: a line with no real test or no working code.
- **Scope creep**: behaviour, files or dependencies the ticket did not ask for.
- **Wrong**: looks implemented, but the implementation is incorrect.

Quote the Done-when line for each finding.

## Axis 2: Standards

- Breaches of a documented rule: cite the file and the rule. These can be hard findings.
- Edits to `AGENTS.md`, `CLAUDE.md`, `.claude/` or `.github/`, a skipped or weakened test: always hard findings.
- Smells, always judgement calls and never blocking on their own: a name that hides what it holds,
  duplicated logic in the diff, abstraction no line asked for, a function that only delegates.
- Skip anything lint or CI already enforces.

## Axis 3: Security

CI already scans for committed secrets; this axis covers what needs judgement. Every confirmed
finding here is a hard finding. Check the diff for:

- **Secrets and personal data**: keys, tokens or passwords in code, tests, fixtures or logs; real
  personal data anywhere; personal data written to logs, error messages or URLs.
- **Untrusted input**: anything from a user, a file, a URL or an external API that reaches a query,
  a shell command, a file path, HTML or `eval` without parameterising, escaping or validating.
- **Access**: a new endpoint, page or command that skips the authentication or authorisation the
  rest of the app uses; permissions or scopes wider than the ticket needs.
- **Undeclared risk**: personal data handled or a paid API called while the ticket's Risk areas
  say "no".
- **Dependencies**: a new package the ticket did not allow, or one that is unmaintained or
  obviously misspelled (a lookalike of a popular name).
- The repo's own rules in `docs/security.md`, if present.

Say "none found" only after checking each bullet; name what you checked.

## Verdict

- **approved**: no hard finding on any axis.
- **changes**: at least one hard finding. Each finding says what is wrong, where (file and line)
  and the smallest fix.

Findings outside the ticket's scope are not changes for this PR: list them under "Follow-ups",
three at most, one line each. Never open an issue for them.

## Output

The first three sections are a short summary in plain language: no jargon, no file names unless
a file is a new part of the app. Base them on the diff, never on the PR body.

```
## In plain words
<2 or 3 sentences: what changes for the person using the app>
## What to look at
<1 to 3 concrete things the owner should check before merging: a screen, a behaviour; or
"Nothing special.">
## Risks
<1 to 3 lines: what could go wrong for users or data if this is merged, and how hard it is to
undo; or "Low: <why>.">
## Spec
<findings, or "No findings.">
## Standards
<findings, or "No findings.">
## Security
<findings, or "None found: checked ...">
## Follow-ups
<up to three out-of-scope lines, or "None.">
Verdict: approved | changes
```

Keep the axes apart: do not merge or rerank them. Under 600 words in total.
