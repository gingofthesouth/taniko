---
name: taniko-validate-run
description: Validate a completed agent run or phase against its evidence before accepting it — diff against the true base, lint the routing log, read the verify documents, count executed tests, and demand denominators. Use at every phase boundary and whenever a node, run, or agent claims completion.
---

# Validate a run against its evidence

An agent's green self-report is not evidence. In the project this suite came
from, four separate integrity holes shipped behind green reports, and every
one was caught by a human reading an artifact — none by the report. Run this
ritual before accepting any run, node, or phase as done.

## The ritual, in order

**1. Diff against the true base.**
`git diff <base>...<tip> --stat`, plus `git status` for untracked files —
plain `git diff` hides them. A content-producing run must show a tip that
differs from its base; an unchanged tree legitimately replays a passing
verdict, so PASS alone proves nothing about work done.
*Earned: five phases of orchestration ran "verified" while the pipeline had
never carried content — every green verdict was a cached replay of the
unchanged base tree; one git command in a preserved worktree exposed it.*

**2. Validate the routing log against BOTH the schema and the grammar lint.**
Schema-valid records can still form an illegal sequence (unbalanced brackets,
double closes, implausible timestamps).
*Earned: the lint's first live catch was a grammar violation that both the
agent's report and human report-based grading had missed.*

**3. Read the verify documents themselves.**
`mode` must be `real` — demo/stub documents never satisfy done-evidence
regardless of verdict. The declared profile's tiers must actually appear in
the stages, and timestamps must be plausible against the run window.
*Earned: a stub verifier emitted profile "full" with two static stages, a
2 ms duration, and a January-1 start date — schema-valid throughout.*

**4. Count executed tests; ignore created files.**
Promised tests must exist by name AND appear in the executed counts. The
proof is a denominator delta in the verify counts (e.g. 822 → 825 after the
verifier added three tests). A test file that never ran is dead code wearing
a test's name.

**5. Demand denominators — the non-vacuous evidence rule.**
Every "checked", "resolves", or "passes" claim must carry its N: "3 of 3
evidence refs resolved", never "evidence resolves". Where gate activity
exists, N must be greater than zero — a gate that cites zero evidence is
vacuously green and must be treated as a warning, not a pass.
*Earned: our own lint printed "evidence resolves" while having checked zero
evidence references — the same disease as the lying demo verifier, committed
by the validator itself.*

**6. Read the strain notes for tone.**
Specific mechanical friction ("field X wouldn't fit shape Y") means the agent
looked. Emptiness or vagueness means it didn't look — not that the schemas
are perfect. An empty strain file is a finding about the run, not the specs.

**7. Run one live command that exercises the claimed fix.**
Not the whole suite — one command aimed at the specific claim. Machines
verify claims against evidence; a human verifies the evidence measures the
right thing.

## Acceptance line

Accept only when all seven hold. If any narrative — the agent's report, a UI
counter, a summary — disagrees with an artifact, the artifact is the
authority; interrogate it first, the command is cheap.
*Earned: a client UI reported "+9,283" changed lines; `git diff --numstat`
showed 156 real insertions.*
