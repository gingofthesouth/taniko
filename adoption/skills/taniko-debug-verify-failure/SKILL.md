---
name: taniko-debug-verify-failure
description: Diagnose a failed verify or run from its bounded feedback — start from the failure's own provenance, search retained evidence narrowly instead of reading logs whole, distinguish fail from error, and verify the diagnosis against the raw artifact. Use whenever a verify, node, or run fails or times out.
---

# Debug a verify failure without drowning the context

Bounded feedback is a contract: the summary you got is deliberately small,
and the raw evidence was retained on disk for exactly this moment. This
skill is the escalation path — without it, agents either flail on the
summary or dump whole logs into context.

## 1. Start from the failure's own provenance

Use the run id, log path, and report paths printed by the failure itself —
never pick up a log by directory listing or recency guess. If a failure
didn't print its provenance, that's a harness bug to fix before diagnosing
anything.
*Earned: a failed run printed no run id or log path; the reviewer picked up
a different run's log and nearly diagnosed fabricated evidence.*

## 2. Classify: fail vs error

- **fail** — the gate judged the code deterministically. Work the feedback:
  the failing assertion, file, and line.
- **error** — the pipeline itself broke (tool missing, timeout, precondition
  failure, no result bundle). An error is a harness/loop bug to repair; it
  never counts as a pass and must never be downgraded to a softened claim.

Timeout errors deserve one extra question: **is the timeout downstream of
the real cause?**
*Earned: a verifier's 900 s timeout headline turned out to be a retry's
fresh session hitting a provisioning gap from the previous attempt. The
real root cause was two steps upstream of the loudest symptom. Two related
mechanics: undrained subprocess pipes turned instant exits into 900 s
timeouts — drain stdout and stderr concurrently while waiting. And a cold
build in a fresh worktree (~80 s) is deterministic pre-work: the orchestrator
runs it before the session, never inside the agent's timeout budget.*

## 3. Search the retained evidence — don't read it

Query narrowly: grep the raw log for the failing test's name, the assertion
text, the seq numbers around the failure. Never inline a whole log into
model context — a 40k-token log is paid for twice, once in tokens and once
in degraded attention. The bounded summary plus targeted searches is the
designed pair.

## 4. Verify the diagnosis against the artifact before acting

Every summary between you and the raw log — the agent's report, the lint's
one-liner, your own first reading — is a place for errors to live. Before
implementing a fix, re-derive the mechanism from the raw artifact.
*Earned: the first lint-based diagnosis of a real grammar violation guessed
"missing enter record"; the raw log showed balanced brackets per attempt and
a duplicate exit record emitted only on the escalation path — a different
bug with a different fix. Prefer artifact-level invariants as the fix (the
appender now rejects a double close; the run lints its own completed log)
over per-code-path patches: artifact checks catch the paths nobody tested.*

## 5. Route the fix to its home layer

Every failure has exactly one home: lost state, stale environment, redundant
reads, permission surprises → **harness**; claimed success contradicted by
reality, runaway retries, noisy feedback → **loop**; wrong order, needless
serialization, misrouting, unbounded cycles, cross-branch contamination →
**graph**. "Improve the prompt" is the correct fix only when all three
layers already hold — it is the last resort, not the first.
*Earned: instructions were escalated twice at a problem that was an
environment defect; the layer diagnosis rule exists because of it.*
