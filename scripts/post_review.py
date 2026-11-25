"""SubagentStop hook for punchlist:reviewer, cloud mode only.

Takes the reviewer's report, exactly as the reviewer wrote it (from its last message or its
transcript), and posts it on the PR with
a hidden marker naming the commit it reviewed and the verdict. The writer never touches this
text. Then:
- approved: the PR leaves draft and is assigned to the owner;
- changes, for the third time on this PR: the PR gets `needs-you` and goes to the owner.

Every run leaves its result (posted, or why not) in a status file that the Stop hook reports,
so a review that does not land is explained instead of retried blindly.
"""

import json
import os
import re
import tempfile

from common import (
    MARKER, MAX_REVIEWS, active, gh, open_pr, read_input, repo, reviews, run, run_with_error,
    to_owner, write_status,
)

# The last line of the report. Tolerant of Markdown emphasis, a heading mark and trailing
# punctuation ("**Verdict: approved**", "Verdict: Approved."), which a strict match missed.
VERDICT_RE = re.compile(r"^[\s>#*_-]*Verdict[*_]*\s*:\s*[*_]*\s*(approved|changes)\b", re.M | re.I)


def strings_in(value):
    """Every string inside a JSON value (a tool call's input can nest the report)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)


def transcript_path(data):
    """The reviewer's own transcript: given by the hook, or next to the session's transcript."""
    path = data.get("agent_transcript_path")
    if path:
        return path
    session, agent = data.get("transcript_path") or "", data.get("agent_id") or ""
    if session.endswith(".jsonl") and agent:
        return os.path.join(session[: -len(".jsonl")], "subagents", f"agent-{agent}.jsonl")
    return ""


def find_review(data):
    """The reviewer's report: the last text it wrote that ends in a verdict line.

    The report can arrive as its last message or inside the call that hands it back to the
    writer, so the reviewer's transcript is searched too. Returns "" if there is none.
    """
    candidates = [data.get("last_assistant_message") or ""]
    path = transcript_path(data)
    try:
        with open(path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = (entry.get("message") or {}).get("content")
                candidates.extend(strings_in(content))
    except OSError:
        pass
    for text in reversed(candidates):
        if VERDICT_RE.search(text or ""):
            return text.strip()
    return ""


def posted_marker(agent_id):
    """One post per reviewer run (the reviewer stops more than once): a file per run."""
    return os.path.join(tempfile.gettempdir(), f"punchlist-posted-{agent_id or 'unknown'}")


def post_comment(r, number, body):
    """Post the review, retrying once; returns "" on success or the error text."""
    error = ""
    for _ in range(2):
        ok, error = run_with_error("gh", "api", f"repos/{r}/issues/{number}/comments", "-f", f"body={body}")
        if ok:
            return ""
    return error or "unknown error"


def main():
    if not active():
        return
    data = read_input()
    message = find_review(data)
    pr = open_pr()
    # No verdict anywhere means no review: post nothing; the Stop hook asks for one again.
    if not pr:
        write_status("not posted: no open PR found for the current branch")
        return
    if not message:
        write_status("not posted: the reviewer's report has no line `Verdict: approved` or `Verdict: changes`")
        return
    marker = posted_marker(data.get("agent_id"))
    # An earlier stop of this same run already posted; only a successful post sets the marker.
    if data.get("agent_id") and os.path.exists(marker):
        return
    verdict = VERDICT_RE.findall(message)[-1].lower()
    sha = pr["head"]["sha"]
    body = MARKER.format(sha=sha, verdict=verdict) + "\n\n" + message
    r, number = repo(), pr["number"]
    error = post_comment(r, number, body)
    if error:
        write_status(f"not posted: GitHub refused the comment ({error})")
        return
    with open(marker, "w") as f:
        f.write("1")
    write_status(f"posted: verdict {verdict} on commit {sha[:7]}")

    if verdict == "approved":
        # `gh pr ready` uses GraphQL; if a proxy blocks it, the PR stays draft and the owner is
        # still assigned, which is the signal that it waits for them.
        run("gh", "pr", "ready", str(number))
        owner = r.split("/")[0]
        gh(f"repos/{r}/issues/{number}/assignees", "-f", f"assignees[]={owner}")
    elif verdict == "changes" and len(reviews(number)) >= MAX_REVIEWS:
        # On the PR, next to the reviews, so its whole history stays in one place.
        to_owner(number, f"Not approved after {MAX_REVIEWS} reviews; the reviews above say what is left.")


if __name__ == "__main__":
    main()
