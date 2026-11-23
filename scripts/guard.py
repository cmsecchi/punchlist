"""PreToolUse hook on Bash, cloud mode only.

Two jobs:
- The reviewer subagent may only run read-only commands: `git diff`, `git log`, `git show` and
  GET requests with `gh api`, one command per call, with no pipes or redirections.
- The writer may not post or forge a review: no PR comments or reviews, no marking the PR ready,
  no merge, no direct calls to the GitHub API with curl or wget, no text that mimics the review
  marker. It may still comment on its own ticket (the `needs-you` path in the dev rules).

This is a deterrent, not a wall: writer and reviewer share one machine. The real gates stay
outside the session: CI on GitHub and the person who merges.
"""

import json
import re
import shlex
import sys

from common import REVIEWER, active, read_input, ticket_number

READ_ONLY_GIT = {"diff", "log", "show"}
WRITE_FLAGS = {"-X", "--method", "-f", "-F", "--field", "--raw-field", "--input"}
SHELL_META = re.compile(r"[;&|`<>\n]|\$\(")


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def check_reviewer(command):
    if SHELL_META.search(command):
        deny("Reviewer: one read-only command per call, with no pipes, redirections or chaining.")
    try:
        words = shlex.split(command)
    except ValueError:
        deny("Reviewer: the command could not be parsed.")
    if len(words) >= 2 and words[0] == "git" and words[1] in READ_ONLY_GIT:
        return
    if len(words) >= 3 and words[:2] == ["gh", "api"] and not WRITE_FLAGS & set(words):
        if not any(w.startswith(("-X", "--method=", "-f", "-F")) for w in words[2:]):
            return
    deny("Reviewer: only `git diff`, `git log`, `git show` and GET requests with `gh api` are allowed.")


def check_writer(command):
    lowered = command.lower()
    if "punchlist-review" in lowered:
        deny("Only the review hook writes the review marker.")
    if re.search(r"\bgh\s+pr\s+(ready|review|comment|merge)\b", lowered):
        deny("The writer does not comment on, review, mark ready or merge its PR; the reviewer and the hooks do.")
    if re.search(r"\b(curl|wget)\b", lowered) and "api.github.com" in lowered:
        deny("Use `gh api`, not curl or wget, for GitHub.")
    if re.search(r"\bgh\s+api\b", lowered):
        if re.search(r"/(pulls/\d+/reviews|pulls/\d+/merge|pulls/comments|issues/comments)\b", lowered):
            deny("The writer does not post reviews or edit comments.")
        target = re.search(r"/issues/(\d+)/comments\b", lowered)
        writes = re.search(r"(\s-x\s*(post|patch|put|delete)|\s-f\s|\s-F\s|--field|--raw-field|--input)", command, re.I)
        if target and writes and target.group(1) != ticket_number():
            deny("The writer may comment only on its own ticket, never on the PR.")


def main():
    if not active():
        return
    data = read_input()
    command = (data.get("tool_input") or {}).get("command") or ""
    if data.get("agent_type") == REVIEWER:
        check_reviewer(command)
    else:
        check_writer(command)


if __name__ == "__main__":
    main()
