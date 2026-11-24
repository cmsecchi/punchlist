"""Stop hook, cloud mode only: the writer's session cannot end with an unreviewed PR.

When the writer tries to finish and its branch has an open PR, the session may end only if:
- the latest commit has an approved review posted by the review hook, or
- the PR already has `needs-you` (out of review rounds).
Otherwise the hook blocks the stop and tells the writer what to do next: run the reviewer, or fix
what the review asked. No PR (the writer stopped early, e.g. on `needs-you`) means nothing to
check.

A loop guard hands the PR to the owner after too many blocks, so a stuck session ends.
"""

import os
import sys
import tempfile

from common import active, has_label, open_pr, read_input, reviews, to_owner

MAX_BLOCKS = 8
COUNTER = os.path.join(tempfile.gettempdir(), "punchlist-stop-blocks")


def block(reason, pr_number):
    count = 1
    try:
        with open(COUNTER) as f:
            count = int(f.read() or 0) + 1
    except (OSError, ValueError):
        pass
    if count > MAX_BLOCKS:
        to_owner(pr_number, "The writer's session could not finish the review loop; it stopped here.")
        return
    with open(COUNTER, "w") as f:
        f.write(str(count))
    print(reason, file=sys.stderr)
    sys.exit(2)


def main():
    if not active():
        return
    read_input()
    pr = open_pr()
    if not pr:
        return
    number, sha = pr["number"], pr["head"]["sha"]
    if has_label(number, "needs-you"):
        return
    latest = [v for s, v in reviews(number) if sha.startswith(s) or s.startswith(sha)]
    if latest and latest[-1] == "approved":
        return
    if not latest or latest[-1] == "none":
        block(
            f"PR #{number} has no review of its latest commit. Start the reviewer with the Agent tool, "
            f"subagent_type `punchlist:reviewer`, and a prompt that is only: `Review PR #{number}.` "
            "Do not summarise your work for it.",
            number,
        )
    block(
        f"The latest review of PR #{number} asks for changes. Fix only its hard findings (a test first "
        "for any behaviour change), run `make test` and `make lint`, push, then start the reviewer "
        f"again with only: `Review PR #{number}.`",
        number,
    )


if __name__ == "__main__":
    main()
