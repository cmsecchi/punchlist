"""Shared helpers for punchlist's cloud-mode hooks.

The hooks only act when the session runs with PUNCHLIST_CLOUD=1 (set on the cloud environment
that runs the writer). Anywhere else (a person's own session, the GitHub Actions mode) they exit
at once and change nothing.

GitHub is reached through `gh api` (REST): some cloud proxies block GraphQL, which most
`gh pr` and `gh issue` commands use.
"""

import json
import os
import re
import subprocess
import sys

# Hidden first line of every review comment the hook posts. The Stop hook looks for it, tied to
# the commit that was reviewed, so a review of an older commit does not count.
MARKER = "<!-- punchlist-review sha={sha} verdict={verdict} -->"
MARKER_RE = re.compile(r"<!-- punchlist-review sha=([0-9a-f]{7,40}) verdict=(approved|changes|none) -->")

# Reviews per PR before the ticket goes to the owner with `needs-you` (first review plus two
# fix rounds, as in the Actions mode).
MAX_REVIEWS = 3

REVIEWER = "punchlist:reviewer"


def active():
    return os.environ.get("PUNCHLIST_CLOUD") == "1"


def read_input():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def run(*args):
    """Run a command and return its stdout, or None if it failed."""
    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def gh(path, *extra):
    """GET (or, with extra flags, write to) a GitHub REST path; parsed JSON or None."""
    out = run("gh", "api", path, *extra)
    if out is None:
        return None
    try:
        return json.loads(out) if out.strip() else {}
    except ValueError:
        return None


def repo():
    """owner/repo from the origin URL, whatever host or proxy it points to."""
    url = (run("git", "remote", "get-url", "origin") or "").strip()
    url = re.sub(r"\.git$", "", url)
    parts = re.split(r"[/:]", url)
    return "/".join(parts[-2:]) if len(parts) >= 2 else ""


def branch():
    return (run("git", "branch", "--show-current") or "").strip()


def ticket_number():
    """The ticket is the number the branch starts with (dev rules: `<issue>-<short-name>`)."""
    match = re.match(r"(\d+)-", branch())
    return match.group(1) if match else ""


def open_pr():
    """The open PR whose head is the current branch, or None."""
    r, b = repo(), branch()
    if not r or not b:
        return None
    owner = r.split("/")[0]
    prs = gh(f"repos/{r}/pulls?state=open&head={owner}:{b}")
    return prs[0] if prs else None


def reviews(pr_number):
    """Hook-posted reviews on a PR, oldest first, as (sha, verdict)."""
    comments = gh(f"repos/{repo()}/issues/{pr_number}/comments?per_page=100") or []
    found = []
    for comment in comments:
        match = MARKER_RE.match(comment.get("body") or "")
        if match:
            found.append((match.group(1), match.group(2)))
    return found


def has_label(issue_number, label):
    issue = gh(f"repos/{repo()}/issues/{issue_number}") if issue_number else None
    return bool(issue) and any(l.get("name") == label for l in issue.get("labels", []))


def to_owner(issue_number, comment):
    """Hand a ticket to the owner: `needs-you` label, assignment and one comment."""
    r = repo()
    owner = r.split("/")[0]
    gh(f"repos/{r}/issues/{issue_number}/labels", "-f", "labels[]=needs-you")
    gh(f"repos/{r}/issues/{issue_number}/assignees", "-f", f"assignees[]={owner}")
    gh(f"repos/{r}/issues/{issue_number}/comments", "-f", f"body={comment}")
