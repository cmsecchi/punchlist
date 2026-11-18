---
name: tdd
description: Test-first development against a ticket's Done-when lines, one line at a time (red, green, next). Use when implementing or fixing a ticket, or when asked to work test-first.
---

# Test-first, one Done-when line at a time

Adapted from Matt Pocock's `tdd` skill (MIT, see LICENSE).

The ticket's **Done when** is the spec. Each line becomes one test, written and passed before the
next line is touched. The repo's `AGENTS.md` (developer rules) sets the branch, the attempt cap
and the PR format; this skill is how to write tests worth keeping inside that loop.

## The cycle

1. Pick the next Done-when line.
2. Decide the seam: the public boundary where that line's behaviour is visible (a function, a
   command, an HTTP endpoint, a rendered component). Test there, never against internals.
3. Write one test named after the line's behaviour ("imports a CSV with a header row"). Run only
   that test. It must fail, and fail for the right reason (the behaviour is missing, not a typo or
   an import error).
4. Write the least code that makes it pass. Run only that test again, with quiet output.
5. Next line. Let what this cycle taught you shape the next test.

A failed run is one attempt. The cap lives in the developer rules; respect it.

## What a good test is

- It reads like the Done-when line it proves and survives a rewrite of the code behind the seam.
- Its expected value comes from an independent source: the ticket, a worked example, a known-good
  literal. Never recompute it the way the code does (`assert add(a, b) == a + b` proves nothing).
- It uses made-up data, never real personal data.
- It mocks only what crosses the system boundary (network, clock, paid APIs), never the code's
  own collaborators.

## Anti-patterns

- **All tests first, then all code.** Tests written ahead test imagined behaviour. One line, one
  test, one minimal implementation.
- **Implementation-coupled tests.** Mocking internals, testing private functions, or checking a
  side channel (reading the database instead of using the interface). The tell: the test breaks
  on a refactor that changed no behaviour.
- **Speculative code.** Nothing a Done-when line does not ask for. No "while I'm here".
- **Refactoring inside the loop.** Clean-up belongs to review, not to red-green.

## When a line cannot become a test

Stop and say so on the issue: quote the line and what makes it untestable. Do not invent a weaker
test that passes.
