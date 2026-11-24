"""SubagentStop hook for punchlist:reviewer, cloud mode only.

Takes the reviewer's report, exactly as the reviewer wrote it (from its last message or its
transcript), and posts it on the PR with
a hidden marker naming the commit it reviewed and the verdict. The writer never touches this
text. Then:
- approved: the PR leaves draft and is assigned to the owner;
- changes, for the third time on this PR: the PR gets `needs-you` and goes to the owner.
"""

import json
import os
import re
import tempfile

from common import MARKER, MAX_REVIEWS, active, gh, open_pr, read_input, repo, reviews, run, to_owner

VERDICT_RE = re.compile(r"^Verdict:\s*(approved|changes)\s*$", re.M)


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


def already_posted(agent_id):
    """One post per reviewer run: the reviewer stops more than once."""
    marker = os.path.join(tempfile.gettempdir(), f"punchlist-posted-{agent_id or 'unknown'}")
    if os.path.exists(marker):
        return True
    with open(marker, "w") as f:
        f.write("1")
    return False


def main():
    if not active():
        return
    data = read_input()
    message = find_review(data)
    pr = open_pr()
    # No verdict anywhere means no review: post nothing; the Stop hook asks for one again.
    if not pr or not message or already_posted(data.get("agent_id")):
        return
    verdict = VERDICT_RE.findall(message)[-1]
    sha = pr["head"]["sha"]
    body = MARKER.format(sha=sha, verdict=verdict) + "\n\n" + message
    r, number = repo(), pr["number"]
    gh(f"repos/{r}/issues/{number}/comments", "-f", f"body={body}")

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
