"""SubagentStop hook for punchlist:reviewer, cloud mode only.

Takes the reviewer's final message, exactly as the reviewer wrote it, and posts it on the PR with
a hidden marker naming the commit it reviewed and the verdict. The writer never touches this
text. Then:
- approved: the PR leaves draft and is assigned to the owner;
- changes, for the third time on this PR: the ticket gets `needs-you` and goes to the owner.
"""

import re

from common import (MARKER, MAX_REVIEWS, active, gh, open_pr, read_input, repo, reviews, run,
                    ticket_number, to_owner)


def main():
    if not active():
        return
    data = read_input()
    message = (data.get("last_assistant_message") or "").strip()
    pr = open_pr()
    if not pr:
        return
    found = re.findall(r"^Verdict:\s*(approved|changes)\s*$", message, re.M)
    verdict = found[-1] if found else "none"
    sha = pr["head"]["sha"]
    body = MARKER.format(sha=sha, verdict=verdict) + "\n\n" + (message or "(The reviewer returned no text.)")
    r, number = repo(), pr["number"]
    gh(f"repos/{r}/issues/{number}/comments", "-f", f"body={body}")

    if verdict == "approved":
        # `gh pr ready` uses GraphQL; if a proxy blocks it, the PR stays draft and the owner is
        # still assigned, which is the signal that it waits for them.
        run("gh", "pr", "ready", str(number))
        owner = r.split("/")[0]
        gh(f"repos/{r}/issues/{number}/assignees", "-f", f"assignees[]={owner}")
    elif verdict == "changes" and len(reviews(number)) >= MAX_REVIEWS and ticket_number():
        to_owner(ticket_number(), f"#{number} was not approved after {MAX_REVIEWS} reviews.")


if __name__ == "__main__":
    main()
